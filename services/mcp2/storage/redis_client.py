import os
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PREFIX = "mcp2:"

redis = Redis.from_url(REDIS_URL, decode_responses=True)


def ns(key: str) -> str:
    return f"{PREFIX}{key}"
