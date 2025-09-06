from services.ingest.ingest_service import TickBuffer


def test_dedup_and_batch_insert():
    buf = TickBuffer(batch=2)
    t = {"symbol": "EURUSD", "ts": "2025-01-01T00:00:00Z", "bid": 1.1, "ask": 1.2}
    assert buf.add(t) is False
    assert buf.add(t) is False  # duplicate rejected
    u = {"symbol": "EURUSD", "ts": "2025-01-01T00:00:01Z", "bid": 1.1001, "ask": 1.2001}
    assert buf.add(u) is True   # reaches batch size
    batch = buf.flush()
    assert len(batch) == 2
    assert {b["hash"] for b in batch} and len({b["hash"] for b in batch}) == 2
