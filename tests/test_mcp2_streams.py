import pytest
from fastapi.testclient import TestClient

from services.mcp2.app import app
from services.mcp2.storage import redis_client


@pytest.fixture
def client(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.streams = {}

        async def xrange(self, key, start='-', end='+', count=None):
            entries = self.streams.get(key, [])
            if count is not None:
                entries = entries[:count]
            return entries

    fake = FakeRedis()
    fake.streams[redis_client.ns('trades')] = [
        ('1-0', {'price': '100'}),
        ('2-0', {'price': '101'}),
    ]
    monkeypatch.setattr('services.mcp2.storage.redis_client.redis', fake)
    return TestClient(app)


def test_streams_trades(client):
    resp = client.get('/streams/trades', params={'limit': 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data == [{'id': '2-0', 'fields': {'price': '101'}}]

