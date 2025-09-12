"""Minimal Pulse Discord bot (MVP).

This lightweight bot demonstrates basic Discord integration for the Pulse
stack.  For production deployments with full command support, use
``services/pulse_bot/bot.py``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx
from aiohttp import web

try:  # pragma: no cover - redis optional
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore

try:  # pragma: no cover - discord optional
    import discord
    from discord.ext import commands
except Exception:  # pragma: no cover
    discord = None  # type: ignore
    commands = None  # type: ignore


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
MCP_MEMORY_API_URL = os.getenv("MCP_MEMORY_API_URL", "http://memory.api")
MCP_MEMORY_API_KEY = os.getenv("MCP_MEMORY_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("PULSE_CACHE_TTL", "600"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("pulse_discord_bot")

_redis: Optional["redis.Redis"] = None


async def get_redis() -> Optional["redis.Redis"]:
    """Lazily initialize Redis connection if possible."""

    global _redis
    if _redis is None and redis is not None:
        _redis = await redis.from_url(
            REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis


async def record_interaction(payload: Dict[str, Any]) -> None:
    """Persist the interaction to the memory API."""

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{MCP_MEMORY_API_URL}/memory",
            json=payload,
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
        )


async def fetch_pulse(query: str) -> str:
    """Fetch answer from memory service with Redis caching."""

    r = _redis or await get_redis()
    key = f"pulse:{query}"
    if r is not None:
        cached = await r.get(key)
        if cached:
            return cached

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{MCP_MEMORY_API_URL}/query",
            json={"query": query},
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "")

    if r is not None:
        await r.set(key, answer, ex=CACHE_TTL)

    asyncio.create_task(record_interaction({"query": query, "response": answer}))
    return answer


# ---------------------------------------------------------------------------
# Discord bot setup
# ---------------------------------------------------------------------------
if commands is not None:  # pragma: no branch - allows import without discord
    intents = getattr(discord, "Intents", object)()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.command(name="pulse")
    async def pulse(ctx, *, query: str | None = None) -> None:
        if not query:
            await ctx.send("Usage: !pulse <query>")
            return
        try:
            result = await fetch_pulse(query)
            await ctx.send(result)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("!pulse failed")
            await ctx.send(f"Error: {exc}")
else:  # fallback for tests where discord is stubbed
    bot = None  # type: ignore


# ---------------------------------------------------------------------------
# Simple HTTP healthcheck endpoint
# ---------------------------------------------------------------------------


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_health_server() -> None:  # pragma: no cover - runtime helper
    app = web.Application()
    app.router.add_get("/healthz", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()


async def main() -> None:  # pragma: no cover - runtime helper
    await start_health_server()
    if bot is not None:
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":  # pragma: no cover - manual execution
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no cover - manual exit
        logger.info("Shutting down")
