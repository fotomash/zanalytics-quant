import asyncio
import os
from typing import Any, Dict, Optional

import httpx
from aiohttp import web

try:
    import aioredis
except Exception:  # pragma: no cover - optional dependency
    aioredis = None  # type: ignore

try:
    import discord
    from discord.ext import commands
except Exception:  # pragma: no cover - discord may be unavailable in tests
    discord = None  # type: ignore
    commands = None  # type: ignore

MCP_MEMORY_API_URL = os.getenv("MCP_MEMORY_API_URL", "http://memory.api")
MCP_MEMORY_API_KEY = os.getenv("MCP_MEMORY_API_KEY", "")

_redis: Optional[Any] = None


async def get_redis() -> Any:
    """Lazily initialize Redis connection if possible."""
    global _redis
    if _redis is None and aioredis is not None:  # pragma: no branch - best effort
        _redis = await aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost"))
    return _redis


async def record_interaction(payload: Dict[str, Any]) -> None:
    """Record the interaction to memory service."""
    async with httpx.AsyncClient() as client:  # pragma: no cover - network
        await client.post(
            f"{MCP_MEMORY_API_URL}/store",
            json=payload,
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
        )


async def fetch_pulse(query: str) -> str:
    """Fetch answer from memory service with Redis caching."""
    redis = _redis or await get_redis()
    key = f"pulse:{query}"
    if redis is not None:
        cached = await redis.get(key)
        if cached:
            return cached

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{MCP_MEMORY_API_URL}/recall",
            json={"query": query},
            headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "")

    if redis is not None:
        await redis.set(key, answer, ex=600)

    # Fire and forget recording of the interaction
    asyncio.create_task(record_interaction({"query": query, "response": answer}))

    return answer


# Discord bot setup ---------------------------------------------------------
if commands is not None:  # pragma: no branch - allows module import without discord
    intents = getattr(discord, "Intents", object)()
    _bot = commands.Bot(command_prefix="!", intents=intents)
    decorator = _bot.command(name="pulse")
else:  # fallback for tests where discord is stubbed
    _bot = None  # type: ignore
    decorator = lambda f: f


@decorator
async def pulse(ctx, *, query: str | None = None):
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

def setup_logging() -> None:
    import logging

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    global logger
    logger = logging.getLogger("pulse_discord_bot")


setup_logging()


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/healthz", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()


async def main() -> None:  # pragma: no cover - manual invocation
    await start_health_server()
    if _bot is not None:
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        await _bot.start(token)
