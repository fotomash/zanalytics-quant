import json
import itertools

import pytest

import services.behavioral_scorer.main as bs


class FakeMessage:
    def __init__(self, topic, payload):
        self._topic = topic
        self._payload = payload

    def error(self):
        return None

    def value(self):
        return json.dumps(self._payload).encode("utf-8")

    def topic(self):
        return self._topic


class FakeConsumer:
    def __init__(self, messages):
        self._messages = messages
        self._index = 0

    def subscribe(self, topics):
        pass

    def poll(self, timeout):
        if self._index < len(self._messages):
            msg = self._messages[self._index]
            self._index += 1
            return msg
        raise StopIteration

    def commit(self, msg):
        pass

    def close(self):
        pass


class FakeRedis:
    def __init__(self, *args, **kwargs):
        self.store = {}

    def set(self, key, value):
        self.store[key] = value

    def close(self):
        pass


def _run_service(monkeypatch, messages):
    consumer = FakeConsumer(messages)
    fake_redis = FakeRedis()

    monkeypatch.setattr(bs, "Consumer", lambda *a, **kw: consumer)
    monkeypatch.setattr(bs.redis, "Redis", lambda *a, **kw: fake_redis)

    time_iter = itertools.count(start=0, step=1)
    monkeypatch.setattr(bs.time, "time", lambda: next(time_iter))

    with pytest.raises(StopIteration):
        bs.main()

    return fake_redis


def test_low_maturity_trade_updates_scores(monkeypatch):
    messages = [
        FakeMessage("final-analysis-payloads", {"trader_id": "trader1", "maturity_score": 10}),
        FakeMessage("trade-execution-events", {"trader_id": "trader1"}),
    ]

    fake_redis = _run_service(monkeypatch, messages)
    payload = json.loads(fake_redis.store["behavioral_metrics:trader1"])

    assert payload["analysis_count"] == 1
    assert payload["patience_index"] == 1.0
    assert payload["rapid_trades"] is False


def test_rapid_trade_penalty_applied(monkeypatch):
    messages = [
        FakeMessage("trade-execution-events", {"trader_id": "trader1"}),
        FakeMessage("trade-execution-events", {"trader_id": "trader1"}),
        FakeMessage("trade-execution-events", {"trader_id": "trader1"}),
        FakeMessage("trade-execution-events", {"trader_id": "trader1"}),
    ]

    fake_redis = _run_service(monkeypatch, messages)
    payload = json.loads(fake_redis.store["behavioral_metrics:trader1"])

    assert payload["rapid_trades"] is True
    assert payload["patience_index"] < 1.0
