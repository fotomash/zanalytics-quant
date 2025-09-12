import asyncio
import logging
import os
from typing import Optional

import httpx
import discord
from discord.ext import commands

try:
    import aioredis
except Exception:  # pragma: no cover - redis optional
    aioredis = None

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MCP_MEMORY_API_URL = os.getenv("MCP_MEMORY_API_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = int(os.getenv("PULSE_CACHE_TTL", "60"))

missing = [
    name
    for name, value in [
        ("DISCORD_TOKEN", DISCORD_TOKEN),
        ("MCP_MEMORY_API_URL", MCP_MEMORY_API_URL),
    ]
    if not value
]
if missing:
    raise RuntimeError(
        "Missing required environment variables: " + ", ".join(missing)
    )

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("pulse_discord_bot")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None and aioredis:
        try:
            _redis = await aioredis.from_url(
                REDIS_URL, encoding="utf-8", decode_responses=True
            )
        except Exception:
            logger.exception("Failed to connect to Redis at %s", REDIS_URL)
    return _redis


async def record_interaction(payload: dict) -> None:
    """Best-effort persistence hook to the memory API."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(MCP_MEMORY_API_URL, json={"store": payload}, timeout=10)
    except Exception:
        logger.exception("Failed to persist interaction")


async def fetch_pulse(query: str) -> str:
    cache_key = f"pulse:{query}"
    r = await get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                return cached
        except Exception:
            logger.exception("Redis get failed for %s", cache_key)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            MCP_MEMORY_API_URL, json={"query": query}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    text = data.get("response") or data.get("result") or str(data)

    if r:
        try:
            await r.set(cache_key, text, ex=CACHE_TTL)
        except Exception:
            logger.exception("Redis set failed for %s", cache_key)

    asyncio.create_task(record_interaction({"query": query, "response": text}))
    return text


@bot.event
async def on_ready() -> None:
    logger.info("Logged in as %s", bot.user)


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    logger.exception("Command error", exc_info=error)
    await ctx.send(f"Error: {error}")


@bot.command(name="pulse")
async def pulse(ctx: commands.Context, *, query: str = "") -> None:
    if not query:
        await ctx.send("Usage: !pulse <query>")
        return
    try:
        result = await fetch_pulse(query)
        await ctx.send(result)
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.exception("!pulse failed")
        await ctx.send(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Simple HTTP healthcheck endpoint
# ---------------------------------------------------------------------------
from aiohttp import web


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/healthz", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()


async def main() -> None:
    await start_health_server()
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")
