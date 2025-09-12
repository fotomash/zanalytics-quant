"""Vectorization service.

Consumes final analysis payloads from Kafka, generates embeddings and
persists them to an external vector database.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Tuple

from confluent_kafka import Consumer

from .brown_vector_store_integration import BrownVectorPipeline
from .pipeline import process_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorizationService:
    """Service that batches embeddings and writes them to a vector store."""

    def __init__(
        self,
        batch_size: int = 50,
        vector_store: BrownVectorPipeline | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.vector_store = vector_store or BrownVectorPipeline()
        self.batch: List[Tuple[str, List[float], Dict[str, Any]]] = []
        self.dlq: List[Dict[str, Any]] = []
        self._running = False

    def process_message(self, payload: Dict[str, Any]) -> None:
        """Convert *payload* into an embedding and queue it for persistence.

        The payload must contain a ``"text"`` field. When the internal batch
        reaches ``batch_size`` the vectors are flushed to the vector store. Any
        exception results in the payload being appended to ``dlq``.
        """

        try:
            embedding = process_payload(payload)
            item_id = payload.get("id") or f"{payload.get('symbol', '')}-{payload.get('timestamp', '')}"
            metadata = {
                k: payload.get(k)
                for k in ("symbol", "timeframe", "timestamp")
                if k in payload
            }
            self.batch.append((item_id, embedding.tolist(), metadata))
            if len(self.batch) >= self.batch_size:
                self.flush()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to process payload: %s", exc)
            self.dlq.append({"payload": payload, "error": str(exc)})

    def flush(self) -> None:
        """Persist the current batch to the vector database."""

        if not self.batch:
            return
        for item_id, embedding, metadata in self.batch:
            try:
                self.vector_store.upsert_vector(item_id, embedding, metadata)
            except Exception as exc:  # pragma: no cover - network failures etc.
                logger.error("Vector DB upsert failed: %s", exc)
                self.dlq.append({"id": item_id, "payload": metadata, "error": str(exc)})
        self.batch.clear()

    def run(self) -> None:  # pragma: no cover - simple run loop
        """Run the service until interrupted."""

        self._running = True
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            self.flush()
            self._running = False


def main() -> None:
    """Run the vectorization consumer loop."""

    service = VectorizationService()

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
                logger.error("Kafka error: %s", msg.error())
                continue

            try:
                payload: Dict[str, Any] = json.loads(msg.value().decode("utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to decode message: %s", exc)
                continue

            service.process_message(payload)
    except KeyboardInterrupt:  # pragma: no cover - manual interrupt
        logger.info("Shutting down vectorization service...")
    finally:
        service.flush()
        consumer.close()


if __name__ == "__main__":  # pragma: no cover - manual start
    main()

