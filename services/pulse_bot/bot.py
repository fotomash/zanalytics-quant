import os
import asyncio
from datetime import datetime
from typing import Optional

from pulse_kernel import PulseKernel
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_WHITELIST = {c.strip() for c in os.getenv("TELEGRAM_CHAT_WHITELIST", "").split(",") if c.strip()}

kernel: Optional[PulseKernel] = None


def get_kernel() -> PulseKernel:
    global kernel
    if kernel is None:
        kernel = PulseKernel(os.getenv("PULSE_CONFIG", "pulse_config.yaml"))
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
        "/help – this menu"
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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
