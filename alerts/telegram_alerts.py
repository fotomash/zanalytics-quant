"""Telegram alert utilities.

This module provides a simple, non-blocking notifier for Pulse that sends
concise messages to Telegram.  Alerts are rate-limited per key to avoid
spamming and never raise exceptions in the trading path.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from typing import Any, Dict

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() == "true"
MIN_GAP = float(os.getenv("ALERTS_MIN_INTERVAL_SECONDS", "60"))

_last_sent: Dict[str, float] = {}
_lock = threading.Lock()


def _send(text: str) -> None:
    """Send a message to Telegram if configured."""
    if not (ENABLED and BOT_TOKEN and CHAT_ID):
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        # Alerts must never break the trading loop
        pass


def _should_throttle(key: str) -> bool:
    """Return True if a message for ``key`` was recently sent."""
    now = time.time()
    with _lock:
        last = _last_sent.get(key, 0.0)
        if now - last < MIN_GAP:
            return True
        _last_sent[key] = now
    return False


def notify(event: Dict[str, Any]) -> None:
    """Send a Telegram alert for ``event`` if thresholds are met."""
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

    # High-quality opportunity
    if (
        rs == "allowed"
        and sc is not None
        and sc >= hi
        and tox is not None
        and tox <= float(os.getenv("ALERTS_TOXICITY_LIMIT", "0.30"))
    ):
        key = f"hi:{sym}"
        text = (
            f"🧠 <b>Top signal</b> {sym} — Score {sc} ({grd})\n"
            f"• Toxicity {tox:.2f} | Liquidity {liq if liq is not None else '—'}\n"
            f"• Why: " + ", ".join(reasons[:3])
        )

    # Blocked by risk rules
    if rs in ("blocked", "deny") or (viol and len(viol) > 0):
        key = f"blk:{sym}:{','.join(sorted(set(viol)))}"
        text = f"⛔ <b>Blocked</b> {sym}\n• Reasons: {', '.join(viol) or ', '.join(warn) or 'policy'}"

    # Intraday drawdown / cooldown
    dd_warn = float(os.getenv("ALERTS_DD_INTRADAY_WARN", "0.025"))
    if ddp is not None and ddp >= dd_warn:
        key = f"dd:{int(ddp * 1000)}"
        text = f"📉 <b>Drawdown</b> {ddp * 100:.2f}% — cooldown active"

    # Trade-count / frequency guard
    if tcnt is not None:
        key = key or f"tc:{tcnt}"
        if tcnt in (3, 4, 5):
            text = text or f"🧯 <b>Trade count</b> {tcnt} — frequency guard engaged"

    if key and text and not _should_throttle(key):
        _send(text)


__all__ = ["notify"]

