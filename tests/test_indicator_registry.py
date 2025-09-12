import json
import fakeredis

from metadata import indicator_registry as ir


class DummyProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    def produce(self, topic: str, value: bytes) -> None:  # pragma: no cover - simple stub
        self.messages.append((topic, value))

    def flush(self) -> None:  # pragma: no cover - simple stub
        pass


def test_publish_registry():
    client = fakeredis.FakeRedis(decode_responses=True)
    producer = DummyProducer()

    ir.publish_registry(redis_client=client, kafka_producer=producer)

    data = client.hgetall("indicator_registry")
    assert "1" in data and "2" in data
    meta = json.loads(data["1"])
    assert "Simple" in meta["name"]
    assert any(topic == "indicator_registry" for topic, _ in producer.messages)
