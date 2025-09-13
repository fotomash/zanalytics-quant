from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import hashlib
import os
import time

from llm_redis_bridge import LLMRedisBridge

DEDUPE_TTL_SECONDS = int(os.getenv("WHISPER_DEDUPE_TTL", "300"))


@dataclass
class Whisper:
    id: str
    ts: float
    category: str        # sizing | patience | profit | cooldown | confluence | overconfidence
    severity: str        # info | suggest | warn
    message: str
    reasons: List[Dict[str, Any]]
    actions: List[Dict[str, str]]   # [{"label": "...", "action": "act_move_sl_be"}]
    ttl_seconds: int
    cooldown_key: str
    cooldown_seconds: int
    channel: List[str]   # ["dashboard","discord"]
    journal_ref: Optional[str] = None


@dataclass
class State:
    # Market
    confluence: float                 # 0..100
    confluence_trend_up: bool
    # Behavior (mirror)
    patience_index: float             # 0..100 (higher = calmer)
    patience_drop_pct: float          # vs baseline
    loss_streak: int
    window_minutes: int
    recent_winrate_similar: float     # 0..1
    # Risk (hard layer)
    hard_cooldown_active: bool
    risk_budget_used_pct: float       # 0..1
    trades_today: int
    # Meta
    user_id: str


class Cooldowns:
    """Per-process cooldowns with optional Redis persistence for cross-process dedupe."""
    _store: Dict[str, float] = {}
    _r = None

    @classmethod
    def _redis(cls):
        if cls._r is not None:
            return cls._r
        try:
            import os
            import redis  # type: ignore
            url = os.getenv("REDIS_URL")
            if url:
                cls._r = redis.from_url(url)
            else:
                cls._r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)))
        except Exception:
            cls._r = None
        return cls._r

    @classmethod
    def hit(cls, key: str) -> bool:
        # Redis takes precedence
        r = cls._redis()
        if r is not None:
            try:
                return bool(r.ttl(f"cooldown:{key}") and r.exists(f"cooldown:{key}"))
            except Exception:
                pass
        now = time.time()
        until = cls._store.get(key, 0)
        return now < until

    @classmethod
    def set(cls, key: str, seconds: int) -> None:
        r = cls._redis()
        if r is not None:
            try:
                r.setex(f"cooldown:{key}", int(max(1, seconds)), "1")
                return
            except Exception:
                pass
        cls._store[key] = time.time() + seconds


def _mk_id(prefix: str = "w") -> str:
    return f"{prefix}-{int(time.time()*1000)}"


class WhisperEngine:
    _local_seen: Dict[str, float] = {}

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}

        w = self.cfg.get("whisper", {})
        t = w.get("thresholds", {})
        self.min_confluence_to_prompt = float(t.get("min_confluence_to_prompt", 35))
        self.patience_drop_warn_pct = float(t.get("patience_drop_warn_pct", 40))
        self.loss_streak_soft = int(t.get("loss_streak_soft", 3))
        self.goal_protect_at_pct = float(t.get("goal_protect_at_pct", 0.75))

        r = w.get("rate_limits", {})
        self.cd_default = int(r.get("default_cooldown_seconds", 300))
        self.cd_patience = int(r.get("patience_cooldown_seconds", 900))
        self.channels = list(w.get("channels", ["dashboard", "discord"]))
    def cluster_narrator(self, top_cluster: Dict[str, Any], redis_client, qdrant_client) -> Dict[str, Any]:
        """Compose a narrative for a cluster using historical context and vector search.

        Parameters
        ----------
        top_cluster:
            Metadata for the cluster that needs narration. Expected to contain
            fields like ``cluster_id``/``id``, ``summary``, ``pattern`` and
            optional ``recommendation``.
        redis_client:
            Redis connection used for fetching historical context via
            :class:`LLMRedisBridge`.
        qdrant_client:
            Vector search client (e.g., :class:`BrownVectorPipeline`) used to
            look up similar historical patterns.

        Returns
        -------
        dict
            Structured payload with ``cluster_id``, ``narrative`` and
            ``recommendation`` keys.
        """

        cluster_id = top_cluster.get("cluster_id") or top_cluster.get("id", "unknown")
        summary = top_cluster.get("summary", "")

        # Gather memory context from Redis
        bridge = LLMRedisBridge(redis_client)
        try:
            context = bridge.get_market_intelligence_summary()
        except Exception:
            context = {}

        insight_parts: List[str] = []
        alerts = context.get("risk_alerts") or []
        if alerts:
            alert = alerts[0]
            alert_msg = alert.get("message") or alert.get("name") or str(alert)
            insight_parts.append(f"Risk alert: {alert_msg}")
        correlations = context.get("correlation_analysis") or {}
        if correlations:
            insight_parts.append("Correlation shifts observed")
        if not insight_parts:
            insight_parts.append("No notable historical alerts")

        memory_insight = "; ".join(insight_parts)

        # Query vector store for similar patterns
        similar_note = ""
        matches: List[Dict[str, Any]] = []
        try:
            if hasattr(qdrant_client, "search_similar_patterns"):
                matches = qdrant_client.search_similar_patterns(
                    pattern_type=top_cluster.get("pattern", ""),
                    timeframe=top_cluster.get("timeframe", ""),
                    top_k=3,
                )
            elif hasattr(qdrant_client, "search"):
                # Expect a raw embedding when direct search is available
                matches = qdrant_client.search(top_cluster.get("embedding", []), top_k=3)  # type: ignore[arg-type]
        except Exception:
            matches = []

        if matches:
            similar_note = f" Found {len(matches)} similar historical patterns."

        narrative = f"{summary} {memory_insight}{similar_note}".strip()
        recommendation = top_cluster.get("recommendation") or top_cluster.get("action", "")

        return {
            "cluster_id": cluster_id,
            "narrative": narrative,
            "recommendation": recommendation,
        }

    def evaluate(self, s: State) -> List[Whisper]:
        if s.hard_cooldown_active:
            return [self._supportive_lock(s)]

        cands: List[Whisper] = []

        # 1) Low-confluence reminder
        if s.confluence < self.min_confluence_to_prompt and not Cooldowns.hit(f"{s.user_id}:lowconf"):
            cands.append(self._low_confluence(s))

        # 2) Slicing suggestion (mid & improving + patience falling)
        if (40 <= s.confluence < 60) and s.confluence_trend_up and s.patience_drop_pct >= self.patience_drop_warn_pct \
           and not Cooldowns.hit(f"{s.user_id}:sizing"):
            cands.append(self._slicing(s))

        # 3) Patience soft cooldown (clustered losses)
        if s.loss_streak >= self.loss_streak_soft and s.window_minutes <= 30 and not s.hard_cooldown_active \
           and not Cooldowns.hit(f"{s.user_id}:patience"):
            cands.append(self._patience(s))

        # 4) Goal protection (banking)
        if s.risk_budget_used_pct >= self.goal_protect_at_pct and not Cooldowns.hit(f"{s.user_id}:goalprotect"):
            cands.append(self._goal_protect(s))

        # 5) Overconfidence circuit
        if (s.trades_today >= 2 * max(1, int(60 / max(1, s.window_minutes)))) and not Cooldowns.hit(f"{s.user_id}:overconf"):
            cands.append(self._overconfidence(s))

        return self._dedupe_and_arm_cooldowns(cands, s.user_id)

    # --- renderers -----------------------------------------------------
    def _low_confluence(self, s: State) -> Whisper:
        return Whisper(
            id=_mk_id("lowconf"),
            ts=time.time(),
            category="confluence",
            severity="suggest",
            message=(
                f"Confluence {int(s.confluence)}/100 matches a low-edge zone. "
                f"Recent win-rate on similar setups: {int(100*s.recent_winrate_similar)}%. Proceed?"
            ),
            reasons=[
                {"key": "confluence_score", "value": s.confluence},
                {"key": "recent_winrate_similar", "value": s.recent_winrate_similar},
            ],
            actions=[],
            ttl_seconds=300,
            cooldown_key="lowconf",
            cooldown_seconds=self.cd_default,
            channel=self.channels,
        )

    def _slicing(self, s: State) -> Whisper:
        return Whisper(
            id=_mk_id("sizing"),
            ts=time.time(),
            category="sizing",
            severity="suggest",
            message=(
                "Confluence is mid and improving; consider slicing entries (e.g., 5×0.1%) "
                "instead of one larger order."
            ),
            reasons=[
                {"key": "confluence_score", "value": s.confluence},
                {"key": "confluence_trend_up", "value": s.confluence_trend_up},
                {"key": "patience_drop_pct", "value": s.patience_drop_pct},
            ],
            actions=[{"label": "Size down next entry", "action": "act_size_down"}],
            ttl_seconds=300,
            cooldown_key="sizing",
            cooldown_seconds=self.cd_default,
            channel=self.channels,
        )

    def _patience(self, s: State) -> Whisper:
        return Whisper(
            id=_mk_id("patience"),
            ts=time.time(),
            category="patience",
            severity="warn",
            message=f"{s.loss_streak} quick losses in ~{s.window_minutes} min. Take a 15-minute reset?",
            reasons=[
                {"key": "loss_streak", "value": s.loss_streak},
                {"key": "patience_index", "value": s.patience_index},
            ],
            actions=[{"label": "Start 15-min timer", "action": "act_start_timer_15"}],
            ttl_seconds=900,
            cooldown_key="patience",
            cooldown_seconds=self.cd_patience,
            channel=self.channels,
        )

    def _goal_protect(self, s: State) -> Whisper:
        pct = int(100 * s.risk_budget_used_pct)
        return Whisper(
            id=_mk_id("goalprotect"),
            ts=time.time(),
            category="profit",
            severity="suggest",
            message=f"Risk budget usage at {pct}%. Consider banking: trail 50% or move SL to BE.",
            reasons=[{"key": "risk_budget_used_pct", "value": s.risk_budget_used_pct}],
            actions=[
                {"label": "Trail 50%", "action": "act_trail_50"},
                {"label": "Move SL to BE", "action": "act_move_sl_be"},
            ],
            ttl_seconds=300,
            cooldown_key="goalprotect",
            cooldown_seconds=self.cd_default,
            channel=self.channels,
        )

    def _overconfidence(self, s: State) -> Whisper:
        return Whisper(
            id=_mk_id("overconf"),
            ts=time.time(),
            category="overconfidence",
            severity="warn",
            message="Trade frequency is spiking vs. window. Consider size-down for the next attempt.",
            reasons=[
                {"key": "trades_today", "value": s.trades_today},
                {"key": "window_minutes", "value": s.window_minutes},
            ],
            actions=[{"label": "Size down next entry", "action": "act_size_down"}],
            ttl_seconds=300,
            cooldown_key="overconf",
            cooldown_seconds=self.cd_default,
            channel=self.channels,
        )

    def _supportive_lock(self, s: State) -> Whisper:
        return Whisper(
            id=_mk_id("cooldown"),
            ts=time.time(),
            category="cooldown",
            severity="info",
            message=(
                "Cooling period active. Review journal notes and breathe. "
                "I’ll speak up again once you’re clear."
            ),
            reasons=[{"key": "hard_cooldown_active", "value": True}],
            actions=[],
            ttl_seconds=600,
            cooldown_key="cooling_banner",
            cooldown_seconds=300,
            channel=self.channels,
        )

    # --- utilities -----------------------------------------------------
    def _dedupe_and_arm_cooldowns(self, ws: List[Whisper], user_id: str) -> List[Whisper]:
        r = Cooldowns._redis()
        now = time.time()
        out: List[Whisper] = []
        for w in ws:
            raw = f"{user_id}:{w.category}:{w.message}"
            key = f"whisper:dedupe:{hashlib.sha1(raw.encode()).hexdigest()}"
            skip = False
            if r is not None:
                try:
                    if not r.set(key, "1", ex=DEDUPE_TTL_SECONDS, nx=True):
                        skip = True
                except Exception:
                    pass
            else:
                exp = self._local_seen.get(key, 0)
                if now < exp:
                    skip = True
                else:
                    self._local_seen[key] = now + DEDUPE_TTL_SECONDS
            if skip:
                continue
            Cooldowns.set(f"{user_id}:{w.cooldown_key}", w.cooldown_seconds)
            out.append(w)
        if r is None:
            for k, exp in list(self._local_seen.items()):
                if exp < now:
                    del self._local_seen[k]
        return out


def serialize_whispers(ws: List[Whisper]) -> List[Dict[str, Any]]:
    return [asdict(w) for w in ws]
