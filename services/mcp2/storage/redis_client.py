import os
from typing import Dict, List, Tuple, Any

from redis.asyncio import Redis

# Primary store for MCP2's own keys
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PREFIX = "mcp2:"
redis = Redis.from_url(REDIS_URL, decode_responses=True)

# Streams source; defaults to main Redis (if provided) or REDIS_URL
REDIS_STREAMS_URL = os.getenv(
    "REDIS_STREAMS_URL",
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)
redis_streams = Redis.from_url(REDIS_STREAMS_URL, decode_responses=True)


def ns(key: str) -> str:
    """Apply the local namespace prefix to a key."""
    return f"{PREFIX}{key}"


async def xread(
    streams: Dict[str, str],
    *,
    count: int | None = None,
    block: int | None = None,
) -> List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]:
    """Wrapper around ``XREAD`` that automatically namespaces stream names.

    Parameters
    ----------
    streams: Dict[str, str]
        Mapping of stream names to last IDs to read from.
    count: int | None
        Maximum number of entries to return per stream.
    block: int | None
        Milliseconds to block waiting for data.
    """

    namespaced = {ns(name): last_id for name, last_id in streams.items()}
    return await redis.xread(streams=namespaced, count=count, block=block)


async def xrange(
    stream: str,
    *,
    start: str = "-",
    end: str = "+",
    count: int | None = None,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Wrapper around ``XRANGE`` for a single stream with namespacing."""

    return await redis.xrange(ns(stream), start, end, count=count)
