import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import fakeredis
from services.redis_ml_bridge import RedisMLBridge


def test_publish_writes_to_streams():
    r = fakeredis.FakeRedis(decode_responses=True)
    bridge = RedisMLBridge(redis_client=r, signal_stream="signals", risk_stream="risk")
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
