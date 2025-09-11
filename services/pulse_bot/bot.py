import os
import sys
import asyncio
import importlib.util
import logging
from datetime import datetime
from typing import Optional

# Robust import of PulseKernel regardless of PYTHONPATH/cwd
try:
    from pulse_kernel import PulseKernel
except Exception:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [
        os.path.join(repo_root, "pulse_kernel.py"),
        os.path.join(repo_root, "core", "pulse_kernel.py"),
        os.path.join(repo_root, "_new", "pulse_kernel.py"),
    ]
    loaded = False
    for path in candidates:
        if os.path.exists(path):
            try:
                spec = importlib.util.spec_from_file_location("pulse_kernel", path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["pulse_kernel"] = mod
                    spec.loader.exec_module(mod)
                    PulseKernel = getattr(mod, "PulseKernel")  # type: ignore
                    loaded = True
                    break
            except Exception:
                continue
    if not loaded:
        raise ModuleNotFoundError("Cannot locate pulse_kernel.py in repo root or core/")
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
import json
import threading
import time
try:
    import redis  # optional
except Exception:
    redis = None

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_WHITELIST = {c.strip() for c in os.getenv("TELEGRAM_CHAT_WHITELIST", "").split(",") if c.strip()}
DJANGO_API_URL = (os.getenv("DJANGO_API_URL", "http://django:8000") or "").rstrip('/')
DJANGO_API_TOKEN = (os.getenv("DJANGO_API_TOKEN", "") or "").strip().strip('"')

logger = logging.getLogger(__name__)

kernel: Optional[PulseKernel] = None


def get_kernel() -> PulseKernel:
    global kernel
    if kernel is None:
        cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
        if not os.path.exists(cfg_path):
            logger.warning("Pulse config file %s not found; using defaults", cfg_path)
        kernel = PulseKernel(cfg_path)
    return kernel


def _auth(msg: Message) -> bool:
    if not CHAT_WHITELIST:
        return True
    uid = str(msg.chat.id)
    return uid in CHAT_WHITELIST


async def cmd_help(msg: Message):
    if not _auth(msg):
        return
    await msg.answer(
        "/status – risk & limits\n"
        "/score <SYMBOL> – confluence now (e.g. /score EURUSD)\n"
        "/journal <TEXT> – append a note\n"
        "/stats – today’s stats\n"
        "/break <mins> – voluntary cooling period\n"
        "/help – this menu\n\n"
        "— Protection —\n"
        "/protect_be <ticket> – move SL to BE\n"
        "/protect_trail <ticket> [ratio] – trail SL to lock ratio (default 0.5)"
    )


async def cmd_status(msg: Message):
    if not _auth(msg):
        return
    k = get_kernel()
    st = k.get_status()
    ds = st.get("daily_stats", {})
    await msg.answer(
        f"📊 Status [{datetime.utcnow().strftime('%H:%M:%S')} UTC]\n"
        f"State: {st.get('behavioral_state','n/a')}\n"
        f"Trades: {ds.get('trades_count',0)} / {k.config['risk_limits']['max_trades_per_day']}\n"
        f"P&L: {ds.get('pnl',0):.2f}\n"
        f"Signals active: {st.get('active_signals',0)}"
    )


async def cmd_score(msg: Message):
    if not _auth(msg):
        return
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.answer("Usage: /score EURUSD")
        return
    symbol = parts[1].upper()
    k = get_kernel()
    res = await k.on_frame({"symbol": symbol, "tf": "M15", "df": {}})
    score = res.get("confidence", res.get("score", 0))
    reasons = res.get("reasons", [])
    action = res.get("action", "none")
    await msg.answer(
        f"🎯 {symbol} score: {score}\n"
        f"Action: {action}\n"
        + ("\n".join([f"• {r}" for r in reasons[:5]]) if reasons else "No reasons.")
    )


async def cmd_journal(msg: Message):
    if not _auth(msg):
        return
    text = msg.text.partition(" ")[2].strip()
    if not text:
        await msg.answer("Usage: /journal <your note>")
        return
    k = get_kernel()
    entry = {"timestamp": datetime.utcnow().isoformat(), "type": "note", "data": {"text": text}}
    await k._journal_decision(entry)
    await msg.answer("📝 Journaled.")


async def cmd_stats(msg: Message):
    if not _auth(msg):
        return
    k = get_kernel()
    ds = k.get_status().get("daily_stats", {})
    wins = ds.get("wins", 0)
    losses = ds.get("losses", 0)
    tot = max(1, wins + losses)
    wr = 100.0 * wins / tot
    await msg.answer(
        f"📈 Today\n"
        f"Trades: {ds.get('trades_count',0)}\n"
        f"Wins/Losses: {wins}/{losses} (WR {wr:.1f}%)\n"
        f"P&L: {ds.get('pnl',0):.2f}"
    )


async def cmd_break(msg: Message):
    if not _auth(msg):
        return
    mins = 15
    parts = msg.text.strip().split()
    if len(parts) > 1 and parts[1].isdigit():
        mins = int(parts[1])
    k = get_kernel()
    re = k.risk_enforcer  # type: ignore
    from datetime import timedelta
    re.daily_stats["cooling_until"] = datetime.now() + timedelta(minutes=mins)
    await msg.answer(f"❄️ Cooling period set for {mins} minutes.")


def _protect_call(action: str, ticket: int, symbol: str = None, lock_ratio: float = 0.5) -> str:
    try:
        url = f"{DJANGO_API_URL}/api/v1/protect/position/"
        headers = {"Content-Type": "application/json"}
        if DJANGO_API_TOKEN:
            headers["Authorization"] = f"Token {DJANGO_API_TOKEN}"
        payload = {"action": action, "ticket": int(ticket)}
        if symbol:
            payload["symbol"] = symbol
        if action == "protect_trail_50":
            payload["lock_ratio"] = float(lock_ratio)
        r = requests.post(url, headers=headers, json=payload, timeout=6.0)
        if r.ok and isinstance(r.json(), dict) and r.json().get("ok"):
            return "✅ Protection applied"
        return f"❌ Failed ({r.status_code})"
    except Exception as e:
        return f"❌ Error: {e}"


async def cmd_protect_be(msg: Message):
    if not _auth(msg):
        return
    parts = msg.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("Usage: /protect_be <ticket>")
        return
    ticket = int(parts[1])
    resp = _protect_call("protect_breakeven", ticket)
    await msg.answer(resp)


async def cmd_protect_trail(msg: Message):
    if not _auth(msg):
        return
    parts = msg.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("Usage: /protect_trail <ticket> [ratio]")
        return
    ticket = int(parts[1])
    ratio = 0.5
    if len(parts) >= 3:
        try:
            ratio = float(parts[2])
        except Exception:
            ratio = 0.5
    ratio = max(0.1, min(0.9, ratio))
    resp = _protect_call("protect_trail_50", ticket, lock_ratio=ratio)
    await msg.answer(resp)


def _build_inline_kb(actions):
    try:
        buttons = []
        for a in actions or []:
            label = a.get('label') or 'Action'
            action = a.get('action') or 'ignore'
            buttons.append([InlineKeyboardButton(text=label, callback_data=action)])
        return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    except Exception:
        return None


def _redis_alert_loop(bot: Bot):
    """Background loop to forward 'telegram-alerts' to whitelisted chats."""
    if redis is None:
        return
    try:
        rurl = os.getenv("REDIS_URL")
        if rurl:
            rcli = redis.from_url(rurl)
        else:
            rcli = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)))
        pubsub = rcli.pubsub()
        pubsub.subscribe("telegram-alerts")
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                try:
                    data = json.loads(msg.get("data") or b"{}")
                except Exception:
                    data = {}
                text = data.get("text") or ""
                if not text:
                    continue
                # Build keyboard if actions provided
                kb = _build_inline_kb(data.get('actions'))
                # Broadcast to whitelisted chats or skip if none
                chats = CHAT_WHITELIST or set()
                for chat_id in chats:
                    try:
                        asyncio.run(bot.send_message(chat_id=chat_id, text=text, reply_markup=kb))
                    except Exception:
                        continue
            time.sleep(0.1)
    except Exception:
        return


async def main():
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN")
    bot = Bot(TOKEN)
    dp = Dispatcher()
    dp.message.register(cmd_help, F.text.regexp(r"^/help$"))
    dp.message.register(cmd_status, F.text.regexp(r"^/status$"))
    dp.message.register(cmd_score, F.text.regexp(r"^/score(\s+.+)?$"))
    dp.message.register(cmd_journal, F.text.regexp(r"^/journal(\s+.+)?$"))
    dp.message.register(cmd_stats, F.text.regexp(r"^/stats$"))
    dp.message.register(cmd_break, F.text.regexp(r"^/break(\s+\d+)?$"))
    dp.message.register(cmd_protect_be, F.text.regexp(r"^/protect_be(\s+\d+)$"))
    dp.message.register(cmd_protect_trail, F.text.regexp(r"^/protect_trail(\s+\d+(\s+\d*\.?\d+)?)$"))
    
    # Callback handlers for inline actions
    async def cb_handler(cb: CallbackQuery):
        if not CHAT_WHITELIST or str(cb.message.chat.id) in CHAT_WHITELIST:
            action = cb.data
            # Inline actions are generic; for now just acknowledge
            await cb.answer(f"Received: {action}")
        else:
            await cb.answer("Not authorized", show_alert=True)
    dp.callback_query.register(cb_handler)

    # Start Redis alert forwarder in background
    if redis is not None and CHAT_WHITELIST:
        t = threading.Thread(target=_redis_alert_loop, args=(bot,), daemon=True)
        t.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
def format_telegram(w: dict) -> str:
    lines = [f"🫢 *The Whisperer*\n{w.get('message','')}"]
    reasons = w.get("reasons") or []
    if reasons:
        top = ", ".join([f"{r.get('key')}={r.get('value')}" for r in reasons[:3]])
        lines.append(f"_Why_: {top}")
    return "\n".join(lines)
