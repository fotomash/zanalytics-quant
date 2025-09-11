import os, sys, importlib
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import fakeredis
import services.redis_ml_bridge as bridge_module


def test_publish_writes_to_streams():
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(
        redis_client=r, signal_stream="signals", risk_stream="risk"
    )
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)

    signals = r.xrange("signals")
    assert len(signals) == 1
    _, fields = signals[0]
    assert fields["symbol"] == "EURUSD"
    assert float(fields["risk"]) == 0.2
    assert float(fields["alpha"]) == 0.1
    assert float(fields["confidence"]) == 0.9

    risk_entries = r.xrange("risk")
    assert len(risk_entries) == 1
    _, rfields = risk_entries[0]
    assert rfields["symbol"] == "EURUSD"
    assert float(rfields["risk"]) == 0.2


def test_default_versioned_streams(monkeypatch):
    monkeypatch.delenv("ML_SIGNAL_STREAM", raising=False)
    monkeypatch.delenv("ML_RISK_STREAM", raising=False)
    monkeypatch.setenv("STREAM_VERSION", "2")
    importlib.reload(bridge_module)
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(redis_client=r)
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)
    assert r.xlen("ml:signals:v2") == 1
    assert r.xlen("ml:risk:v2") == 1


def test_backward_compatible_streams(monkeypatch):
    monkeypatch.setenv("STREAM_VERSION", "3")
    monkeypatch.setenv("ML_SIGNAL_STREAM", "ml:signals")
    monkeypatch.setenv("ML_RISK_STREAM", "ml:risk")
    importlib.reload(bridge_module)
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(redis_client=r)
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)
    assert r.xlen("ml:signals") == 1
    assert r.xlen("ml:risk") == 1
