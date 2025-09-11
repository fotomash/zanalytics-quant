import fakeredis

from services.redis_ml_bridge import RedisMLBridge


def test_publish_to_signal_and_risk_streams():
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = RedisMLBridge(redis_client=r, signal_stream="sig", risk_stream="risk")
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
