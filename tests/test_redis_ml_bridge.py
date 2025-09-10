import json
import os
import sys

import fakeredis
import redis

# Ensure project root is on path for importing the bridge
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from integration.redis_ml_bridge import RedisMLBridge


def test_bridge_publishes_structured_signal():
    r = fakeredis.FakeRedis()
    bridge = RedisMLBridge(redis_client=r, input_channel="in", output_channel="out")
    out = r.pubsub()
    out.subscribe("out")

    # establish subscription to input channel
    bridge.run_once()

    r.publish("in", json.dumps({"foo": "bar"}))
    bridge.run_once()

    # discard subscription confirmation
    out.get_message(timeout=1.0)
    msg = out.get_message(timeout=1.0)
    assert msg is not None
    data = json.loads(msg["data"])
    assert data["payload"] == {"foo": "bar"}
    assert "timestamp" in data


def test_bridge_reconnects(monkeypatch):
    r = fakeredis.FakeRedis()
    bridge = RedisMLBridge(redis_client=r, input_channel="in", output_channel="out", retry_interval=0)
    out = r.pubsub()
    out.subscribe("out")

    bridge.run_once()  # initial connection

    original_get_message = bridge.pubsub.get_message
    calls = {"n": 0}

    def failing_get_message(*args, **kwargs):
        if calls["n"] == 0:
            calls["n"] += 1
            raise redis.ConnectionError("boom")
        return original_get_message(*args, **kwargs)

    monkeypatch.setattr(bridge.pubsub, "get_message", failing_get_message)

    # first run triggers reconnection
    bridge.run_once()

    # after reconnection, publish a message and ensure it's processed
    r.publish("in", json.dumps({"v": 1}))
    # first call may consume subscription confirmation
    bridge.run_once()
    bridge.run_once()

    out.get_message(timeout=1.0)
    msg = out.get_message(timeout=1.0)
    assert msg is not None
    assert json.loads(msg["data"])["payload"] == {"v": 1}

