from __future__ import annotations

from typing import Any, Dict

from . import rt as _rt


class PulseClient:
    """Tiny convenience client for Pulse real‑time helpers.

    Wraps Redis-based utilities with a simple OO interface. If Redis is not
    configured/reachable, helpers fail gracefully.
    """

    def publish_whisper(self, payload: Dict[str, Any]) -> bool:
        return _rt.publish_whisper(payload)

    def start_cooldown(self, key: str, seconds: int) -> bool:
        return _rt.start_cooldown(key, seconds)

    def seen_once(self, key: str, ttl_seconds: int = 300) -> bool:
        return _rt.seen_once(key, ttl_seconds)


__all__ = ["PulseClient"]

