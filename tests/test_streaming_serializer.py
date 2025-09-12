import json

import fakeredis

from utils import streaming


class DummyProducer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, bytes]] = []

    def produce(self, topic: str, value: bytes) -> None:  # pragma: no cover - simple stub
        self.messages.append((topic, value))

    def flush(self) -> None:  # pragma: no cover - simple stub
        pass


def test_serialize_fallback(monkeypatch):
    data = {"a": 1}
    # normal path uses msgpack
    encoded = streaming.serialize(data)
    assert isinstance(encoded, (bytes, bytearray))

    # force MessagePack failure to trigger JSON fallback
    monkeypatch.setattr(streaming.msgpack, "packb", lambda *a, **k: (_ for _ in ()).throw(TypeError()))
    encoded = streaming.serialize(data)
    assert encoded == json.dumps(data).encode("utf-8")


def test_publish_redis_and_kafka():
    redis_client = fakeredis.FakeRedis()
    producer = DummyProducer()

    streaming.publish(
        "42",
        {"value": 1},
        {"symbol": "XYZ"},
        redis_client=redis_client,
        kafka_producer=producer,
    )

    assert redis_client.lpop("stream:42") is not None
    assert redis_client.hgetall("stream:metadata:42") == {b"symbol": b"XYZ"}
    assert ("stream:42", streaming.serialize({"value": 1})) in producer.messages
    assert ("stream:metadata:42", streaming.serialize({"symbol": "XYZ"})) in producer.messages

