import os
import json
import time
import threading
from typing import Optional

import redis
from services.common import get_logger

try:
    from confluent_kafka import Producer  # type: ignore
except Exception:  # pragma: no cover
    Producer = None  # type: ignore


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TICKS_PATTERN = os.getenv("TICKS_PATTERN", "ticks.*")  # Pub/Sub pattern
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")

logger = get_logger(__name__)


def kafka_topic_for(channel: str) -> str:
    # Map Redis pubsub channel (e.g., ticks.BTCUSDT) directly to Kafka
    return channel


def main() -> None:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    if Producer is None:
        logger.error("confluent_kafka not available; exiting")
        return
    try:
        p = Producer({"bootstrap.servers": KAFKA_BROKERS})
    except Exception:
        logger.error("Failed to init Kafka producer; exiting")
        return

    pubsub = r.pubsub()
    pubsub.psubscribe(TICKS_PATTERN)
    logger.info(
        "Mirroring Redis pubsub '%s' to Kafka @ %s", TICKS_PATTERN, KAFKA_BROKERS
    )
    try:
        for msg in pubsub.listen():
            if msg is None:
                continue
            if msg.get("type") not in ("pmessage", "message"):
                continue
            channel = msg.get("channel") or msg.get("pattern")
            payload = msg.get("data")
            if not channel or not payload:
                continue
            try:
                topic = kafka_topic_for(str(channel))
                # Pass-through JSON; ensure bytes
                if not isinstance(payload, (bytes, bytearray)):
                    payload = str(payload).encode("utf-8")
                p.produce(topic, payload)
            except Exception:
                continue
    finally:
        try:
            p.flush(2.0)
        except Exception:
            pass


if __name__ == "__main__":
    main()

