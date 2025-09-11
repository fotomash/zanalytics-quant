
from __future__ import annotations

from typing import Any, Dict, List

from core.ingestion_engine import IngestionEngine
from core.bootstrap_engine import BootstrapEngine


class DummyMessage:
    def __init__(self, value: bytes) -> None:
        self._value = value

    def value(self) -> bytes:  # pragma: no cover - simple accessor
        return self._value

    def error(self) -> None:  # pragma: no cover - no errors in tests
        return None


class DummyConsumer:
    def __init__(self, messages: List[DummyMessage]) -> None:
        self.messages = messages
        self.topics: List[str] = []

    def subscribe(self, topics: List[str]) -> None:
        self.topics = topics

    def poll(self, timeout: float) -> DummyMessage | None:
        if self.messages:
            return self.messages.pop(0)
        return None

    def close(self) -> None:  # pragma: no cover - no-op
        pass


class DummyBootstrap(BootstrapEngine):
    def boot(self) -> None:  # type: ignore[override]
        self.session_manifest = {"kafka": {"brokers": "dummy:9092"}}


def test_profile_registration_and_poll() -> None:
    captured_cfg: List[Dict[str, Any]] = []
    msg = DummyMessage(b"payload")

    def consumer_factory(cfg: Dict[str, Any]) -> DummyConsumer:
        captured_cfg.append(cfg)
        return DummyConsumer([msg])

    handled: List[bytes] = []

    def handler(m: DummyMessage) -> None:
        handled.append(m.value())

    engine = IngestionEngine(
        bootstrap=DummyBootstrap(),
        consumer_factory=consumer_factory,
    )
    engine.register_profile({"topic": "test.topic", "handler": handler})

    # Ensure consumer was created with session-aware broker config
    assert captured_cfg[0]["bootstrap.servers"] == "dummy:9092"

    # Simulate one poll cycle and ensure handler invoked
    engine.poll()
    assert handled == [b"payload"]

    # Consumer should have subscribed to provided topic
    consumer = engine.consumers["test.topic"]
    assert consumer.topics == ["test.topic"]
