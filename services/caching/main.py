import os
import json
import signal
from typing import Any, Dict, Optional

import redis
from confluent_kafka import Consumer, KafkaError


KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "caching-service")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "enriched-analysis-payloads")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

LATEST_PAYLOAD_TTL = int(os.getenv("LATEST_PAYLOAD_TTL", "3600"))
ACTIVE_FVG_TTL = int(os.getenv("ACTIVE_FVG_TTL", "3600"))
BEHAVIORAL_SCORE_TTL = int(os.getenv("BEHAVIORAL_SCORE_TTL", "3600"))


def _create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BROKERS,
            "group.id": KAFKA_GROUP,
            "auto.offset.reset": "earliest",
        }
    )


def _create_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _handle_payload(r: redis.Redis, payload_str: str) -> None:
    try:
        payload: Dict[str, Any] = json.loads(payload_str)
    except json.JSONDecodeError:
        print("Invalid JSON payload")
        return

    symbol: Optional[str] = payload.get("symbol")
    timeframe: Optional[str] = payload.get("timeframe")
    trader_id: Optional[str] = payload.get("trader_id")

    if symbol and timeframe:
        r.setex(
            f"latest_payload:{symbol}:{timeframe}",
            LATEST_PAYLOAD_TTL,
            payload_str,
        )

    fvg = payload.get("fvg_signal")
    if symbol and fvg is not None:
        r.setex(
            f"active_fvg_signals:{symbol}",
            ACTIVE_FVG_TTL,
            json.dumps(fvg),
        )

    behavioral = payload.get("behavioral_score")
    if trader_id and behavioral is not None:
        r.setex(
            f"current_behavioral_score:{trader_id}",
            BEHAVIORAL_SCORE_TTL,
            str(behavioral),
        )


def main() -> None:
    consumer = _create_consumer()
    redis_client = _create_redis_client()

    running = True

    def _signal_handler(sig, frame):  # type: ignore[no-untyped-def]
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    consumer.subscribe([KAFKA_TOPIC])
    print(
        f"Caching service consuming '{KAFKA_TOPIC}' from {KAFKA_BROKERS} and writing to Redis@{REDIS_HOST}:{REDIS_PORT}"
    )

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            print(f"Consumer error: {msg.error()}")
            continue

        payload_str = msg.value().decode("utf-8")
        _handle_payload(redis_client, payload_str)

    consumer.close()


if __name__ == "__main__":
    main()
