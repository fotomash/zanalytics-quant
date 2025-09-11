"""Kafka ingestion engine for agents and services.

This module provides a light‑weight orchestration layer around Kafka
consumers and producers.  It is intentionally small and test friendly;
real Kafka clients are optional and may be substituted with mocks in
unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional
import os

try:  # pragma: no cover - optional dependency
    from confluent_kafka import Consumer, Producer
except Exception:  # pragma: no cover - handled gracefully
    Consumer = Producer = None  # type: ignore[misc,assignment]

from core.bootstrap_engine import BootstrapEngine


Handler = Callable[[Any], None]


@dataclass
class Profile:
    """Configuration for a single topic pipeline."""

    topic: str
    handler: Handler
    group_id: str | None = None


class IngestionEngine:
    """Manage Kafka consumers/producers and dispatch message pipelines.

    The engine builds on :class:`BootstrapEngine` for environment and
    session configuration.  Profiles representing agents or services can
    be registered to specify topics and their corresponding message
    handlers.  The engine then polls all registered consumers and routes
    messages to the appropriate handlers.
    """

    def __init__(
        self,
        bootstrap: BootstrapEngine | None = None,
        consumer_factory: Optional[Callable[[Dict[str, Any]], Any]] = None,
        producer_factory: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        self.bootstrap = bootstrap or BootstrapEngine()
        # Initialise shared settings (env vars, manifests, etc.)
        self.bootstrap.boot()
        self.session_cfg = self.bootstrap.session_manifest or {}

        self.consumer_factory = consumer_factory or self._default_consumer
        self.producer_factory = producer_factory or self._default_producer

        self.consumers: Dict[str, Any] = {}
        self.producers: Dict[str, Any] = {}
        self.handlers: Dict[str, Handler] = {}

    # ------------------------------------------------------------------
    # Factories
    def _default_consumer(self, config: Dict[str, Any]) -> Any:
        if Consumer is None:  # pragma: no cover - missing optional dep
            raise RuntimeError("confluent_kafka is required for consumers")
        return Consumer(config)

    def _default_producer(self, config: Dict[str, Any]) -> Any:
        if Producer is None:  # pragma: no cover - missing optional dep
            raise RuntimeError("confluent_kafka is required for producers")
        return Producer(config)

    # ------------------------------------------------------------------
    # Registration
    def register_profile(self, profile: Profile | Dict[str, Any]) -> None:
        """Register a profile specifying topic and handler.

        Parameters
        ----------
        profile:
            Either a :class:`Profile` instance or a dictionary containing
            ``topic`` and ``handler`` keys and optional ``group_id``.
        """

        if isinstance(profile, dict):
            profile = Profile(**profile)
        if not profile.group_id:
            profile.group_id = "ingestion-engine"

        brokers = (
            self.session_cfg.get("kafka", {}).get("brokers")
            or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        )
        consumer_cfg = {
            "bootstrap.servers": brokers,
            "group.id": profile.group_id,
            "auto.offset.reset": "earliest",
        }
        consumer = self.consumer_factory(consumer_cfg)
        consumer.subscribe([profile.topic])

        self.consumers[profile.topic] = consumer
        self.handlers[profile.topic] = profile.handler

    # ------------------------------------------------------------------
    # Producers
    def get_producer(self, topic: str) -> Any:
        if topic not in self.producers:
            brokers = (
                self.session_cfg.get("kafka", {}).get("brokers")
                or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
            )
            producer_cfg = {"bootstrap.servers": brokers}
            self.producers[topic] = self.producer_factory(producer_cfg)
        return self.producers[topic]

    def produce(self, topic: str, key: Optional[str], value: bytes) -> None:
        """Send a message to ``topic`` using or creating a producer."""
        producer = self.get_producer(topic)
        producer.produce(topic, key=key, value=value)

    # ------------------------------------------------------------------
    # Polling
    def poll(self, timeout: float = 0.1) -> None:
        """Poll all consumers once and dispatch messages to handlers."""
        for topic, consumer in self.consumers.items():
            msg = consumer.poll(timeout)
            if msg is None:
                continue
            err = getattr(msg, "error", lambda: None)()
            if err:  # pragma: no cover - network errors
                continue
            handler = self.handlers.get(topic)
            if handler is not None:
                handler(msg)

    def run_forever(self, timeout: float = 1.0) -> None:
        """Continuously poll consumers until interrupted."""
        try:
            while True:
                self.poll(timeout)
        except KeyboardInterrupt:  # pragma: no cover - manual stop
            pass
        finally:
            for consumer in self.consumers.values():
                close = getattr(consumer, "close", None)
                if callable(close):
                    close()
            for producer in self.producers.values():
                flush = getattr(producer, "flush", None)
                if callable(flush):
                    flush()
