import fakeredis
import importlib
import services.redis_ml_bridge as bridge_module


def test_publish_to_signal_and_risk_streams():
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(
        redis_client=r, signal_stream="sig", risk_stream="risk"
    )
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)

    sig_entries = r.xrange("sig")
    risk_entries = r.xrange("risk")
    assert len(sig_entries) == 1
    assert len(risk_entries) == 1
    _, sig_fields = sig_entries[0]
    _, risk_fields = risk_entries[0]
    assert sig_fields["symbol"] == "EURUSD"
    assert risk_fields["symbol"] == "EURUSD"
    assert "timestamp" in sig_fields
    assert "timestamp" in risk_fields


def test_default_versioned_keys(monkeypatch):
    monkeypatch.delenv("ML_SIGNAL_STREAM", raising=False)
    monkeypatch.delenv("ML_RISK_STREAM", raising=False)
    monkeypatch.setenv("STREAM_VERSION", "4")
    importlib.reload(bridge_module)
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(redis_client=r)
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)
    assert r.xlen("ml:signals:v4") == 1
    assert r.xlen("ml:risk:v4") == 1


def test_legacy_keys(monkeypatch):
    monkeypatch.setenv("STREAM_VERSION", "4")
    monkeypatch.setenv("ML_SIGNAL_STREAM", "ml:signals")
    monkeypatch.setenv("ML_RISK_STREAM", "ml:risk")
    importlib.reload(bridge_module)
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = bridge_module.RedisMLBridge(redis_client=r)
    bridge.publish("EURUSD", 0.2, 0.1, 0.9)
    assert r.xlen("ml:signals") == 1
    assert r.xlen("ml:risk") == 1
