import os
import requests
from typing import Dict

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram(message: str) -> bool:
    """Send a message via Telegram bot. Returns True if successful."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message}
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception:
        return False


def alert_event(event: Dict) -> None:
    """Send Telegram alerts based on risk/score events."""
    decision = event.get("decision", {})
    score_info = event.get("score", {})
    features = event.get("features", {})
    symbol = event.get("symbol", "")

    score_val = score_info.get("score")
    status = decision.get("status")
    reasons = decision.get("reason", [])
    toxicity = features.get("toxicity")

    # Trade allowed
    if status == "allowed":
        if score_val is not None and score_val >= 90 and (toxicity is None or toxicity <= 0.3):
            send_telegram(f"\U0001F9E0 {symbol} Top Signal – Score: {score_val:.0f}")
        else:
            send_telegram(f"\u2705 Signal allowed – {symbol} – Score: {score_val:.0f}")

    # Trade blocked or warned
    elif status in {"blocked", "warned"}:
        reason_text = "; ".join(reasons)
        if toxicity is not None and toxicity > 0.3:
            send_telegram(f"\u26A0\uFE0F Blocked: Toxicity {toxicity:.2f} > limit")
        elif reason_text:
            prefix = "\u26A0\uFE0F" if status == "blocked" else "\u26A0\uFE0F"
            send_telegram(f"{prefix} {reason_text}")

    # Daily limit reached
    if any("daily loss limit" in r.lower() for r in reasons):
        send_telegram("\u26D4 Daily cap hit. All signals blocked.")

    # Cooldown alerts
    if any("cooling off period" in r.lower() for r in reasons):
        send_telegram("\uD83D\uDD04 Cooldown started")

    # Drawdown alert if available
    raw = decision.get("raw", {})
    account = raw.get("account_state", {})
    try:
        daily_pnl = abs(account.get("daily_pnl", 0))
        starting = account.get("starting_equity") or 0
        if starting and daily_pnl / starting > 0.025:
            send_telegram(f"\U0001F4C9 Intraday DD: {daily_pnl / starting:.1%} – cooling triggered")
    except Exception:
        pass
