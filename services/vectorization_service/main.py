"""Vectorization service.

Consumes final analysis payloads from Kafka and sends them through the
vectorizer pipeline.
"""

import json
import logging
import os
from typing import Any, Dict

from confluent_kafka import Consumer

from .pipeline import process_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the vectorization consumer loop."""
    conf = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "group.id": os.getenv("KAFKA_GROUP_ID", "vectorization-service"),
        "auto.offset.reset": "earliest",
    }
    topic = os.getenv("KAFKA_ANALYSIS_TOPIC", "final-analysis-payloads")

    consumer = Consumer(conf)
    consumer.subscribe([topic])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Kafka error: {msg.error()}")
                continue

            try:
                payload: Dict[str, Any] = json.loads(msg.value().decode("utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                logger.error(f"Failed to decode message: {exc}")
                continue

            try:
                process_payload(payload)
            except Exception as exc:  # pragma: no cover - pipeline errors
                logger.error(f"Pipeline error: {exc}")
    except KeyboardInterrupt:
        logger.info("Shutting down vectorization service...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
