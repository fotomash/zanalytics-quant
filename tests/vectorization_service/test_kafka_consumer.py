from typing import Any
from unittest.mock import MagicMock
import sys
import types


class MockMessage:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def value(self) -> bytes:
        return self._payload

    def error(self) -> None:
        return None


def test_kafka_consumer_loop(monkeypatch):
    # Provide a dummy confluent_kafka module before importing main
    dummy_module = types.SimpleNamespace(Consumer=object)
    sys.modules.setdefault("confluent_kafka", dummy_module)

    from services.vectorization_service import main as vmain

    messages = [
        MockMessage(b"{\"a\": 1}"),
        MockMessage(b"{\"b\": 2}"),
    ]
    consumer = MagicMock()
    consumer.poll.side_effect = messages + [KeyboardInterrupt()]
    consumer.subscribe.return_value = None
    consumer.close.return_value = None

    monkeypatch.setattr(vmain, "Consumer", lambda conf: consumer)
    processed: list[dict[str, Any]] = []
    monkeypatch.setattr(vmain, "process_payload", lambda payload: processed.append(payload))

    vmain.main()

    assert processed == [{"a": 1}, {"b": 2}]
    assert consumer.subscribe.called
    assert consumer.close.called
