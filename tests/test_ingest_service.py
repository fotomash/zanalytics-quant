import asyncio
import pytest

from services.ingest.ingest_service import insert_batch

class FailingConn:
    def __init__(self, fail_times=1):
        self.fail_times = fail_times
        self.calls = 0
        self.rollbacks = 0

    async def executemany(self, *args, **kwargs):
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise Exception("db error")

    async def rollback(self):
        self.rollbacks += 1

@pytest.mark.asyncio
async def test_insert_batch_rolls_back_and_retries(monkeypatch):
    conn = FailingConn(fail_times=1)
    async def no_sleep(_):
        pass
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    batch = [{"symbol": "EURUSD", "ts": "t", "bid": 1, "ask": 2, "hash": "h"}]
    await insert_batch(conn, batch, max_retries=2, base_delay=0)
    assert conn.rollbacks == 1
    assert conn.calls == 2

@pytest.mark.asyncio
async def test_insert_batch_raises_after_retries(monkeypatch):
    conn = FailingConn(fail_times=3)
    async def no_sleep(_):
        pass
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    batch = [{"symbol": "EURUSD", "ts": "t", "bid": 1, "ask": 2, "hash": "h"}]
    with pytest.raises(Exception):
        await insert_batch(conn, batch, max_retries=2, base_delay=0)
    assert conn.rollbacks == 2
    assert conn.calls == 2
