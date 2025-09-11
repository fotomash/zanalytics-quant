import os
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
    return f"{PREFIX}{key}"
