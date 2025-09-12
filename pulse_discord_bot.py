import sys
from services.pulse_discord_bot import pulse_discord_bot as _impl
sys.modules[__name__] = _impl

import asyncio
import os
from typing import Any, Dict, Optional

import httpx

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
    """Minimal Pulse Discord bot (MVP).

    This lightweight bot demonstrates basic Discord integration for the Pulse stack.
    For production deployments with full command support, use
    ``services/pulse_bot/bot.py``.
    """
    pass
This lightweight bot demonstrates basic Discord integration for the Pulse
stack.  For production deployments with full command support, use
``services/pulse_bot/bot.py``.

The bot expects a ``DISCORD_BOT_TOKEN`` environment variable for authentication.
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


import discord
from discord.ext import commands

try:
    import aioredis
except Exception:  # pragma: no cover - redis optional
    aioredis = None  # type: ignore


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MCP_MEMORY_API_URL = os.getenv("MCP_MEMORY_API_URL", "http://memory.api")
MCP_MEMORY_API_KEY = os.getenv("MCP_MEMORY_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = int(os.getenv("PULSE_CACHE_TTL", "60"))

missing = [
    name
    for name, value in [
        ("DISCORD_BOT_TOKEN", DISCORD_BOT_TOKEN),
        ("MCP_MEMORY_API_URL", MCP_MEMORY_API_URL),
        ("MCP_MEMORY_API_KEY", MCP_MEMORY_API_KEY),
    ]
    if not value
]
if missing:
    raise RuntimeError(
        "Missing required environment variables: " + ", ".join(missing)
    )
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


_redis: Optional[aioredis.Redis] = None  # type: ignore[name-defined]
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
async def get_redis() -> Optional[aioredis.Redis]:
    """Lazily create a Redis connection."""
    global _redis
    if _redis is None and aioredis:
        try:
            _redis = await aioredis.from_url(  # type: ignore[attr-defined]
                REDIS_URL, encoding="utf-8", decode_responses=True
            )
        except Exception:  # pragma: no cover - best effort only
            logger.exception("Failed to connect to Redis at %s", REDIS_URL)
    return _redis


async def record_interaction(payload: dict) -> None:
    """Best-effort persistence hook to the memory API."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{MCP_MEMORY_API_URL}/store",
                json=payload,
                headers={"Authorization": f"Bearer {MCP_MEMORY_API_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            logger.error(
                "Authentication failed persisting interaction - check MCP_MEMORY_API_KEY"
                "Memory API authentication failed; check MCP_MEMORY_API_KEY"
            )
        else:
            logger.exception("Failed to persist interaction")
    except Exception:
        logger.exception("Failed to persist interaction")


async def fetch_pulse(query: str) -> str:
    """Query the Pulse memory API with Redis caching."""
    cache_key = f"pulse:{query}"
    r = await get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                return cached
        except Exception:  # pragma: no cover - best effort only
            logger.exception("Redis get failed for %s", cache_key)

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
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                logger.error(
                    "Authentication failed querying memory API - check MCP_MEMORY_API_KEY"
                )
                raise RuntimeError(
                    "Authentication with memory API failed: invalid or missing MCP_MEMORY_API_KEY"
                ) from exc
                msg = "Memory API authentication failed; check MCP_MEMORY_API_KEY"
                logger.error(msg)
                raise RuntimeError(msg) from exc
            raise
        data = resp.json()

    text = data.get("response") or data.get("result") or str(data)

    if r:
        try:
            await r.set(cache_key, text, ex=CACHE_TTL)
        except Exception:  # pragma: no cover - best effort only
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
    """Handle the !pulse command by querying the memory API."""

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
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    import logging

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    global logger
    logger = logging.getLogger("pulse_discord_bot")


setup_logging()



async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_health_server() -> None:  # pragma: no cover - runtime helper
    app = web.Application()
    app.router.add_get("/healthz", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()

async def main() -> None:  # pragma: no cover - manual invocation
    if _bot is not None:
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        await _bot.start(token)
    await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no cover - shutdown path
if __name__ == "__main__":  # pragma: no cover - manual execution
    try:
        asyncio.run(main())
    except KeyboardInterrupt:  # pragma: no cover - manual exit
        logger.info("Shutting down")

    except Exception as exc:  # pragma: no cover - error path
        logger.exception("Unhandled exception in main", exc_info=exc)
