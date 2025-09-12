from __future__ import annotations

import json
from typing import Any, Dict

from utils import streaming

# Map of registry ID to human readable indicator metadata.
# Each entry describes an indicator configuration that may be
# referenced in real-time tick streams.
INDICATOR_REGISTRY: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Simple Moving Average (20)",
        "description": "20 period simple moving average",
        "params": {"period": 20},
    },
    2: {
        "name": "Relative Strength Index (14)",
        "description": "14 period relative strength index",
        "params": {"period": 14},
    },
}

# Reverse lookup to translate indicator names used in code to
# registry identifiers. This allows producers to emit compact
# numeric IDs in tick streams.
NAME_TO_ID: Dict[str, int] = {
    "SMA_20": 1,
    "RSI_14": 2,
}


def publish_registry(*, redis_client=None, kafka_producer=None) -> None:
    """Publish indicator metadata to Redis and Kafka.

    Each registry entry is published once per configuration so that
    consumers can cache the metadata locally.
    """
    for reg_id, meta in INDICATOR_REGISTRY.items():
        if redis_client is not None:
            redis_client.hset("indicator_registry", reg_id, json.dumps(meta))
        if kafka_producer is not None:
            kafka_producer.produce(
                "indicator_registry", streaming.serialize({"id": reg_id, **meta})
            )
            kafka_producer.flush()


def get_id(name: str) -> int | None:
    """Return the registry ID for an indicator key such as ``SMA_20``."""
    return NAME_TO_ID.get(name)


__all__ = ["INDICATOR_REGISTRY", "NAME_TO_ID", "publish_registry", "get_id"]
