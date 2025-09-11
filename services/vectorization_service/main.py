import logging
import time
from typing import List
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


class VectorizationService:
    """Simple service that converts incoming messages to vectors."""

    def __init__(self) -> None:
        self._running = False

    # Startup method: initialize resources
    def startup(self) -> None:
        """Prepare the service for processing messages."""
        logger.info("Starting VectorizationService...")
        self._running = True

    # Shutdown method: cleanup
    def shutdown(self) -> None:
        """Clean up resources before shutting down."""
        logger.info("Shutting down VectorizationService...")
        self._running = False

    # Process message method
    def process_message(self, message: str) -> List[int]:
        """Convert a message into a list of character codes.

        Args:
            message: Text message to vectorize.
        Returns:
            List of integer code points representing the message.
        """
        try:
            logger.debug("Vectorizing message: %s", message)
            return [ord(ch) for ch in message]
        except Exception as exc:  # pragma: no cover - log and re-raise
            logger.error("Failed to vectorize message: %s", exc)
            raise

    # Main run loop
    def run(self) -> None:
        """Run the service until interrupted."""
        self.startup()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            self.shutdown()


if __name__ == "__main__":
    service = VectorizationService()
    service.run()

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
