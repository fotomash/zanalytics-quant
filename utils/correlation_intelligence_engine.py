from __future__ import annotations

import json
import time
import os
from typing import Any, Dict, Tuple

from services.mcp2.llm_config import call_local_echo, call_whisperer
from session_manifest import load_prompt
try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


_ESCALATIONS: dict[Tuple[str, str, float], float] = {}
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _RCLI = None
if redis is not None:
    try:
        _RCLI = redis.from_url(_REDIS_URL, decode_responses=True)
    except Exception:
        _RCLI = None


def recently_escalated(key: Tuple[str, str, float], within_secs: int = 120) -> bool:
    """Check dedupe window using Redis if available; fallback to in-memory."""
    if _RCLI is not None:
        try:
            skey = f"dedupe:escalate:{key[0]}:{key[1]}:{key[2]:.2f}"
            return _RCLI.ttl(skey) > 0 if _RCLI.exists(skey) else False
        except Exception:
            pass
    ts = _ESCALATIONS.get(key)
    return bool(ts and (time.time() - ts) < within_secs)


def mark_escalated(key: Tuple[str, str, float], within_secs: int = 120) -> None:
    """Mark escalation with Redis TTL if available; fallback to in-memory."""
    if _RCLI is not None:
        try:
            skey = f"dedupe:escalate:{key[0]}:{key[1]}:{key[2]:.2f}"
            _RCLI.setex(skey, max(5, within_secs), "1")
            return
        except Exception:
            pass
    _ESCALATIONS[key] = time.time()


def _json_or_raise(text: str) -> Dict[str, Any]:
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def aware_caution_tick(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate caution locally; escalate to Whisperer if high.

    ctx must contain fields referenced by aware_caution_v1.
    """
    AWARE_RUNS.inc()
    prompt = load_prompt("aware_caution_v1").format(**ctx)
    echo_raw = call_local_echo(prompt)
    try:
        out = _json_or_raise(echo_raw)
    except Exception:
        # Tolerate non-JSON local output by downgrading to no caution
        out = {"caution": "none", "reason": "non-json", "suggest": "hold"}

    ctx["caution"] = out.get("caution")
    ctx["caution_reason"] = out.get("reason")
    ctx["caution_suggest"] = out.get("suggest")

    key = (str(ctx.get("symbol", "?")), str(ctx.get("phase", "?")), round(float(ctx.get("corr_cluster", 0.0)), 2))
    if out.get("caution") == "high" and not recently_escalated(key, within_secs=120):
        AWARE_ESCALATIONS.inc()
        wprompt = load_prompt("what_if_surge_masks_trap_v1").format(**ctx)
        wraw = call_whisperer(wprompt)
        try:
            wout = _json_or_raise(wraw)
        except Exception:
            wout = {"ae_pct": None, "rr_if_hedged": None, "rule_tweak": None}
        ctx["ae_pct"] = wout.get("ae_pct")
        ctx["rr_if_hedged"] = wout.get("rr_if_hedged")
        ctx["rule_tweak"] = wout.get("rule_tweak")
        mark_escalated(key)
    return ctx


# Metrics (optional; exposed when imported under MCP2 app)
try:
    from prometheus_client import Counter, REGISTRY  # type: ignore

    AWARE_RUNS = Counter(
        "aware_caution_runs_total", "Total aware_caution evaluations", registry=REGISTRY
    )
    AWARE_ESCALATIONS = Counter(
        "aware_caution_escalations_total", "Total escalations to Whisperer", registry=REGISTRY
    )
except Exception:  # pragma: no cover
    class _Dummy:
        def inc(self, *_, **__):
            return None

    AWARE_RUNS = _Dummy()
    AWARE_ESCALATIONS = _Dummy()
