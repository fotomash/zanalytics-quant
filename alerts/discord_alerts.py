"""Discord alert utilities.

Alerts are delivered via a Discord webhook. Alerts are rate limited per
key and failures are silent so trading paths are never disrupted.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from typing import Any, Dict, Optional

import yaml

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None  # type: ignore


def _load_config() -> Dict[str, Any]:
    path = os.getenv("ALERT_CONFIG", "config/alert_config.yaml")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
            dc = cfg.get("discord", {})
            return {k: os.path.expandvars(v) if isinstance(v, str) else v for k, v in dc.items()}
    except Exception:
        return {}


_DC_CFG = _load_config()
WEBHOOK_URL = _DC_CFG.get("webhook_url") or os.getenv("DISCORD_WEBHOOK_URL", "")
ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() == "true"
MIN_GAP = float(os.getenv("ALERTS_MIN_INTERVAL_SECONDS", "60"))

_last_sent: Dict[str, float] = {}
_lock = threading.Lock()
_rds: Optional["redis.Redis"] = None


def _redis_client() -> Optional["redis.Redis"]:
    global _rds
    if _rds is not None:
        return _rds
    if not redis:
        return None
    try:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _rds = redis.from_url(url)
        return _rds
    except Exception:
        return None


def _send(text: str) -> None:
    """Send ``text`` to Discord if configured."""
    if not (ENABLED and WEBHOOK_URL):
        return
    data = json.dumps({"content": text}).encode()
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _should_throttle(key: str) -> bool:
    """Return True if a message for ``key`` was recently sent."""
    try:
        r = _redis_client()
        if r is not None:
            k = f"pulse:alerts:dedupe:{key}"
            created = r.set(k, str(int(time.time())), ex=max(1, int(MIN_GAP)), nx=True)
            if created:
                return False
            return True
    except Exception:
        pass
    now = time.time()
    with _lock:
        last = _last_sent.get(key, 0.0)
        if now - last < MIN_GAP:
            return True
        _last_sent[key] = now
    return False


def notify(event: Dict[str, Any]) -> None:
    """Send a Discord alert for ``event`` if thresholds are met."""
    if not ENABLED:
        return

    sym = event.get("symbol", "—")
    sc = event.get("score")
    grd = event.get("grade")
    rs = event.get("risk_status") or event.get("decision")
    reasons = event.get("reasons") or []
    metrics = event.get("metrics") or {}
    account = event.get("account") or {}

    tox = metrics.get("toxicity")
    liq = metrics.get("liq_score")
    ddp = account.get("dd_intraday")
    tcnt = account.get("trades_today")
    warn = event.get("warnings") or []
    viol = event.get("violations") or []

    key = None
    text = None

    hi = float(os.getenv("ALERTS_SCORE_HI", "90"))

    if (
        rs == "allowed"
        and sc is not None
        and sc >= hi
        and tox is not None
        and tox <= float(os.getenv("ALERTS_TOXICITY_LIMIT", "0.30"))
    ):
        key = f"hi:{sym}"
        text = (
            f"🧠 **Top signal** {sym} — Score {sc} ({grd})\n"
            f"• Toxicity {tox:.2f} | Liquidity {liq if liq is not None else '—'}\n"
            f"• Why: " + ", ".join(reasons[:3])
        )

    if rs in ("blocked", "deny") or (viol and len(viol) > 0):
        key = f"blk:{sym}:{','.join(sorted(set(viol)))}"
        text = f"⛔ **Blocked** {sym}\n• Reasons: {', '.join(viol) or ', '.join(warn) or 'policy'}"

    dd_warn = float(os.getenv("ALERTS_DD_INTRADAY_WARN", "0.025"))
    if ddp is not None and ddp >= dd_warn:
        key = f"dd:{int(ddp * 1000)}"
        text = f"📉 **Drawdown** {ddp * 100:.2f}% — cooldown active"

    if tcnt is not None:
        key = key or f"tc:{tcnt}"
        if tcnt in (3, 4, 5):
            text = text or f"🧯 **Trade count** {tcnt} — frequency guard engaged"

    if key and text and not _should_throttle(key):
        _send(text)


__all__ = ["notify"]
