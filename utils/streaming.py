"""Streaming helpers with MessagePack serialization.

This module provides a minimal interface for publishing data streams to
Redis lists or Kafka topics using MessagePack for compact binary
serialization.  If ``msgpack`` is not available or data cannot be encoded
as MessagePack, JSON is used as a fallback so callers do not need to worry
about dependency availability.

Metadata accompanying a stream is written separately to
``stream:metadata:{id}`` either as a Redis hash or a dedicated Kafka
topic.  This mirrors common streaming patterns where high‑volume payloads
are stored independently from lighter descriptive metadata.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
try:  # pragma: no cover - optional dependency
    import msgpack  # type: ignore

    _HAS_MSGPACK = True
except Exception:  # pragma: no cover - msgpack is optional
    msgpack = None  # type: ignore
    _HAS_MSGPACK = False


def serialize(data: Any) -> bytes:
    """Serialize ``data`` using MessagePack when available.

    Falls back to JSON if ``msgpack`` is missing or the object cannot be
    encoded by the MessagePack serializer.
    """

    if _HAS_MSGPACK:
        try:  # attempt binary encoding first
            return msgpack.packb(data, use_bin_type=True)  # type: ignore[arg-type]
        except Exception:
            pass
    return json.dumps(data).encode("utf-8")


# ---------------------------------------------------------------------------
# Publishing helpers
# ---------------------------------------------------------------------------
def publish(
    stream_id: str,
    payload: Any,
    metadata: Optional[Mapping[str, Any]] = None,
    *,
    redis_client: Optional[Any] = None,
    kafka_producer: Optional[Any] = None,
    topic_prefix: str = "stream",
) -> None:
    """Publish ``payload`` and optional ``metadata``.

    Parameters
    ----------
    stream_id:
        Identifier of the logical stream (used for Redis keys or Kafka topics).
    payload:
        The primary data structure to publish.
    metadata:
        Optional metadata dictionary.  If provided, it is written to
        ``stream:metadata:{id}`` separately from the main payload.
    redis_client / kafka_producer:
        Either or both may be supplied.  ``redis_client`` must provide an
        ``rpush`` method and ``hset`` for metadata.  ``kafka_producer`` must
        provide ``produce`` and ``flush`` methods.
    topic_prefix:
        Prefix for the Redis key or Kafka topic.  Defaults to ``"stream"``.
    """

    encoded = serialize(payload)
    stream_key = f"{topic_prefix}:{stream_id}"

    if redis_client is not None:
        redis_client.rpush(stream_key, encoded)
        if metadata:
            redis_client.hset(f"{topic_prefix}:metadata:{stream_id}", mapping=metadata)

    if kafka_producer is not None:
        kafka_producer.produce(stream_key, encoded)
        kafka_producer.flush()
        if metadata:
            kafka_producer.produce(
                f"{topic_prefix}:metadata:{stream_id}", serialize(metadata)
            )
            kafka_producer.flush()


__all__ = ["serialize", "publish"]

