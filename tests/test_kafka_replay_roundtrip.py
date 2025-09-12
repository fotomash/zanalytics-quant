from __future__ import annotations

import sys
import types

from backend.mt5.mt5_bridge import serialize_ticks

# Provide a dummy confluent_kafka module before importing the consumer.
dummy_kafka = types.SimpleNamespace(
    Consumer=object,
    KafkaError=types.SimpleNamespace(_PARTITION_EOF=0),
    TopicPartition=object,
)
sys.modules.setdefault("confluent_kafka", dummy_kafka)

from ops.kafka import replay_consumer as rc


class DummyMessage:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def value(self) -> bytes:  # pragma: no cover - simple accessor
        return self._payload

    def error(self):  # pragma: no cover - tests always supply valid messages
        return None


def test_produced_message_round_trip(capsys):
    ticks = [{"time": 1, "bid": 1.2345, "ask": 1.2347, "volume": 10}]
    payload = serialize_ticks(ticks)

    # Simulate consumer processing of the produced payload
    rc.process_messages([DummyMessage(payload)])

    # The consumer prints the deserialized ticks; ensure it matches
    out = capsys.readouterr().out
    assert str(ticks) in out

    # And ensure the explicit deserializer returns the original ticks
    assert rc.deserialize_ticks(payload) == ticks
