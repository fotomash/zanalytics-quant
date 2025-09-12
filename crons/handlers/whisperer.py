import logging
import time
from typing import Any, Mapping

import redis

logger = logging.getLogger(__name__)


def enqueue(
    redis_client: "redis.Redis",
    stream: str,
    payload: Mapping[str, Any],
    *,
    maxlen: int = 1000,
    retries: int = 3,
    backoff: float = 0.5,
) -> Any:
    """Add ``payload`` to ``stream`` using ``redis_client.xadd``.

    Wraps the call in ``try/except redis.RedisError`` and logs failures with
    context. Retries with exponential ``backoff`` up to ``retries`` times.
    Returns the message ID on success or ``None`` on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            return redis_client.xadd(stream, payload, maxlen=maxlen, approximate=True)
        except redis.RedisError as exc:  # pragma: no cover - log path
            logger.warning(
                "xadd failed for stream %s (attempt %s/%s): %r",
                stream,
                attempt,
                retries,
                payload,
                exc_info=exc,
            )
            time.sleep(backoff * attempt)
    return None
