"""EWT enrichment and alert publishing utilities."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import redis

from .processors import AdvancedProcessor
from .streaming import serialize

EWT_TOPIC = os.getenv("EWT_ALERTS_TOPIC", "ewt_alerts")
DATA_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ALERTS_REDIS_URL = os.getenv("ALERTS_REDIS_URL", "redis://localhost:6379/1")


def publish_ewt_alert(
    df: pd.DataFrame,
    *,
    fractals_only: bool = False,
    wave_only: bool = False,
    redis_url: str | None = None,
    alerts_redis_url: str | None = None,
    kafka_producer: Any | None = None,
    topic: str = EWT_TOPIC,
) -> bytes:
    """Process ``df`` and publish an EWT alert.

    Parameters
    ----------
    df:
        Price data expected by :class:`AdvancedProcessor`.
    fractals_only / wave_only:
        Selective output toggles used to keep payloads lean.
    redis_url / alerts_redis_url:
        Optional overrides for the analytics and alerts Redis connections.
    kafka_producer:
        Optional Kafka producer used to mirror alerts to a Kafka topic.
    topic:
        Destination Redis pub/sub channel and Kafka topic name.

    Returns
    -------
    bytes
        The serialized MessagePack payload.
    """

    processor = AdvancedProcessor()
    payload = processor.process(
        df, fractals_only=fractals_only, wave_only=wave_only
    )
    encoded = serialize(payload)

    data_redis = redis.from_url(redis_url or DATA_REDIS_URL)
    alerts_redis = redis.from_url(alerts_redis_url or ALERTS_REDIS_URL)

    # Store for history and publish to alert channel
    data_redis.rpush(topic, encoded)
    alerts_redis.publish(topic, encoded)

    if kafka_producer is not None:  # pragma: no cover - optional integration
        kafka_producer.produce(topic, encoded)
        kafka_producer.flush()

    return encoded


__all__ = ["publish_ewt_alert"]
