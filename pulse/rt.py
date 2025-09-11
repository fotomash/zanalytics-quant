from __future__ import annotations

import os
import json
from typing import Any, Dict

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


def _r():
    if redis is None:
        return None
    url = os.getenv("REDIS_URL")
    try:
        return redis.from_url(url) if url else redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", 6379)))
    except Exception:
        return None


def publish_whisper(payload: Dict[str, Any]) -> bool:
    """Publish a whisper to list and pubsub channel.

    Appends to 'whispers' list and publishes on 'pulse.whispers'.
    Returns True on best-effort success.
    """
    r = _r()
    if r is None:
        return False
    try:
        data = json.dumps(payload)
        r.rpush("whispers", data)
        try:
            r.publish("pulse.whispers", data)
        except Exception:
            pass
        return True
    except Exception:
        return False


def start_cooldown(key: str, seconds: int) -> bool:
    """Start a cooldown if not active; returns True if set, False if already cooling or failure.

    Uses Redis SET with NX and EX to avoid races.
    """
    r = _r()
    if r is None:
        return False
    try:
        # Redis-py set returns True if key was set
        return bool(r.set(f"cooldown:{key}", "1", ex=int(max(1, seconds)), nx=True))
    except Exception:
        return False


def seen_once(key: str, ttl_seconds: int = 300) -> bool:
    """Return True if this key was not seen in the last ttl_seconds and mark it as seen.

    Useful for deduplication across processes.
    """
    r = _r()
    if r is None:
        return True  # behave permissively if Redis missing
    try:
        ok = r.set(f"seen:{key}", "1", ex=int(max(1, ttl_seconds)), nx=True)
        return bool(ok)
    except Exception:
        return True

