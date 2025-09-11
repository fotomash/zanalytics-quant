"""Kafka-backed Telegram alert service."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from confluent_kafka import Consumer, KafkaError

from alerts.telegram_alerts import _send as _send_telegram, _should_throttle


KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "telegram-service")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "telegram-alerts")


def send_alert(payload: Dict[str, Any]) -> None:
    """Send a Telegram alert for ``payload`` if not throttled."""
    text = payload.get("text")
    if not text:
        return
    key = str(payload.get("key") or payload.get("symbol") or hash(text))
    if not _should_throttle(key):
        _send_telegram(text)


def _create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BROKERS,
            "group.id": KAFKA_GROUP,
            "auto.offset.reset": "earliest",
        }
    )


def main() -> None:
    consumer = _create_consumer()
    consumer.subscribe([KAFKA_TOPIC])
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Consumer error: {msg.error()}")
                continue
            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except json.JSONDecodeError:
                print("Invalid JSON payload")
                continue
            send_alert(payload)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
