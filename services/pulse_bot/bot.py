import os
import sys
import importlib.util
import logging
from datetime import datetime
from typing import Optional

import requests
import redis
import discord
from discord.ext import commands

# Robust import of PulseKernel regardless of PYTHONPATH/cwd
try:
    from pulse_kernel import PulseKernel
except Exception:  # pragma: no cover - fallback loader
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

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_WHITELIST = {c.strip() for c in os.getenv("DISCORD_CHANNEL_WHITELIST", "").split(",") if c.strip()}
DJANGO_API_URL = (os.getenv("DJANGO_API_URL", "http://django:8000") or "").rstrip('/')
DJANGO_API_TOKEN = (os.getenv("DJANGO_API_TOKEN", "") or "").strip().strip('"')
REDIS_URL = os.getenv("REDIS_URL")
MCP_MEMORY_API_URL = (os.getenv("MCP_MEMORY_API_URL", "") or "").rstrip("/")
MCP_MEMORY_API_KEY = (os.getenv("MCP_MEMORY_API_KEY", "") or "").strip()

logger = logging.getLogger(__name__)

kernel: Optional[PulseKernel] = None
redis_client: Optional[redis.Redis] = None

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:  # pragma: no cover - connection issues
        logger.error("Failed to connect to Redis at %s: %s", REDIS_URL, e)


def get_kernel() -> PulseKernel:
    global kernel
    if kernel is None:
        cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
        if not os.path.exists(cfg_path):
            logger.warning("Pulse config file %s not found; using defaults", cfg_path)
        else:
            logger.info("Using Pulse config %s", cfg_path)
        kernel = PulseKernel(cfg_path)
    return kernel


def _auth(channel_id: int) -> bool:
    if not CHANNEL_WHITELIST:
        return True
    return str(channel_id) in CHANNEL_WHITELIST


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)


def _recall(prompt: str) -> list[str]:
    if not MCP_MEMORY_API_URL or not MCP_MEMORY_API_KEY:
        return []
    try:
        r = requests.post(
            f"{MCP_MEMORY_API_URL}/recall",
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
            json={"prompt": prompt},
            timeout=5,
        )
        if r.ok:
            data = r.json()
            memories = data.get("memories")
            if isinstance(memories, list):
                return [str(m) for m in memories]
    except Exception as e:  # pragma: no cover - network issues
        logger.error("Memory recall failed: %s", e)
    return []


def _store(prompt: str, response: str) -> None:
    if not MCP_MEMORY_API_URL or not MCP_MEMORY_API_KEY:
        return
    try:
        requests.post(
            f"{MCP_MEMORY_API_URL}/store",
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
            json={"prompt": prompt, "response": response},
            timeout=5,
        )
    except Exception as e:  # pragma: no cover - network issues
        logger.error("Memory store failed: %s", e)


async def _cached_response(prompt: str) -> str:
    key = f"prompt:{prompt}"
    if redis_client:
        cached = redis_client.get(key)
        if cached:
            return cached
    memories = _recall(prompt)
    response = prompt
    if memories:
        response = f"{response}\n" + "\n".join(memories)
    _store(prompt, response)
    if redis_client:
        try:
            redis_client.setex(key, 3600, response)
        except Exception as e:  # pragma: no cover - redis issues
            logger.error("Redis cache set failed: %s", e)
    return response


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith("/"):
        await bot.process_commands(message)
        return
    should_reply = message.guild is None or bot.user in message.mentions
    if not should_reply:
        await bot.process_commands(message)
        return
    prompt = message.content
    if bot.user in message.mentions:
        prompt = prompt.replace(f"<@{bot.user.id}>", "").strip()
    response = await _cached_response(prompt)
    await message.channel.send(response)
    await bot.process_commands(message)


@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    if not _auth(ctx.channel.id):
        return
    await ctx.send(
        "/status – risk & limits\n"
        "/score <SYMBOL> – confluence now (e.g. /score EURUSD)\n"
        "/journal <TEXT> – append a note\n"
        "/stats – today's stats\n"
        "/break <mins> – voluntary cooling period\n"
    )


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    if not _auth(ctx.channel.id):
        return
    k = get_kernel()
    st = k.get_status()
    ds = st.get("daily_stats", {})
    await ctx.send(
        f"📊 Status [{datetime.utcnow().strftime('%H:%M:%S')} UTC]\n"
        f"State: {st.get('behavioral_state','n/a')}\n"
        f"Trades: {ds.get('trades_count',0)} / {k.config['risk_limits']['max_trades_per_day']}\n"
        f"P&L: {ds.get('pnl',0):.2f}\n"
        f"Signals active: {st.get('active_signals',0)}"
    )


@bot.command(name="score")
async def cmd_score(ctx: commands.Context, symbol: str | None = None):
    if not _auth(ctx.channel.id):
        return
    if not symbol:
        await ctx.send("Usage: /score EURUSD")
        return
    symbol = symbol.upper()
    k = get_kernel()
    res = await k.on_frame({"symbol": symbol, "tf": "M15", "df": {}})
    score = res.get("confidence", res.get("score", 0))
    reasons = res.get("reasons", [])
    action = res.get("action", "none")
    lines = [
        f"🎯 {symbol} score: {score}",
        f"Action: {action}",
    ]
    if reasons:
        lines.extend([f"• {r}" for r in reasons[:5]])
    await ctx.send("\n".join(lines))


@bot.command(name="journal")
async def cmd_journal(ctx: commands.Context, *, text: str | None = None):
    if not _auth(ctx.channel.id):
        return
    if not text:
        await ctx.send("Usage: /journal <your note>")
        return
    k = get_kernel()
    entry = {"timestamp": datetime.utcnow().isoformat(), "type": "note", "data": {"text": text}}
    await k._journal_decision(entry)
    await ctx.send("📝 Journaled.")


@bot.command(name="stats")
async def cmd_stats(ctx: commands.Context):
    if not _auth(ctx.channel.id):
        return
    k = get_kernel()
    ds = k.get_status().get("daily_stats", {})
    wins = ds.get("wins", 0)
    losses = ds.get("losses", 0)
    tot = max(1, wins + losses)
    wr = 100.0 * wins / tot
    await ctx.send(
        f"📈 Today\n"
        f"Trades: {ds.get('trades_count',0)}\n"
        f"Wins/Losses: {wins}/{losses} (WR {wr:.1f}%)\n"
        f"P&L: {ds.get('pnl',0):.2f}"
    )


@bot.command(name="break")
async def cmd_break(ctx: commands.Context, mins: int = 15):
    if not _auth(ctx.channel.id):
        return
    k = get_kernel()
    re = k.risk_enforcer  # type: ignore
    from datetime import timedelta
    re.daily_stats["cooling_until"] = datetime.now() + timedelta(minutes=mins)
    await ctx.send(f"❄️ Cooling period set for {mins} minutes.")


def _protect_call(action: str, ticket: int, symbol: str | None = None, lock_ratio: float = 0.5) -> str:
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
    except Exception as e:  # pragma: no cover - network issues
        return f"❌ Error: {e}"


@bot.command(name="protect_be")
async def cmd_protect_be(ctx: commands.Context, ticket: int | None = None):
    if not _auth(ctx.channel.id):
        return
    if ticket is None:
        await ctx.send("Usage: /protect_be <ticket>")
        return
    resp = _protect_call("protect_breakeven", ticket)
    await ctx.send(resp)


@bot.command(name="protect_trail")
async def cmd_protect_trail(ctx: commands.Context, ticket: int | None = None, ratio: float = 0.5):
    if not _auth(ctx.channel.id):
        return
    if ticket is None:
        await ctx.send("Usage: /protect_trail <ticket> [ratio]")
        return
    ratio = max(0.1, min(0.9, ratio))
    resp = _protect_call("protect_trail_50", ticket, lock_ratio=ratio)
    await ctx.send(resp)


@bot.event
async def on_ready():
    logger.info("Discord bot connected as %s", bot.user)


if __name__ == "__main__":
    required = {
        "DISCORD_BOT_TOKEN": TOKEN,
        "REDIS_URL": REDIS_URL,
        "MCP_MEMORY_API_URL": MCP_MEMORY_API_URL,
        "MCP_MEMORY_API_KEY": MCP_MEMORY_API_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        for k in missing:
            logger.error("Environment variable %s is not set", k)
        sys.exit(1)
    bot.run(TOKEN)
