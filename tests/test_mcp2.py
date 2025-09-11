import pytest
from fastapi.testclient import TestClient
from services.mcp2.app import app


@pytest.fixture
def client(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.kv = {}
            self.lst = []

        async def set(self, key, value):
            self.kv[key] = value

        async def get(self, key):
            return self.kv.get(key)

        async def lpush(self, key, value):
            self.lst.insert(0, value)

        async def lrange(self, key, start, end):
            end = None if end == -1 else end + 1
            return self.lst[start:end]

    fake_redis = FakeRedis()
    monkeypatch.setattr(
        'services.mcp2.storage.redis_client.redis', fake_redis
    )

    class FakePool:
        async def fetch(self, query, *args):
            return [{'id': 1, 'content': 'alpha document'}]

    async def fake_get_pool():
        return FakePool()

    monkeypatch.setattr('services.mcp2.storage.pg.get_pool', fake_get_pool)
    monkeypatch.setattr('services.mcp2.routers.tools.get_pool', fake_get_pool)

    return TestClient(app), fake_redis


def test_log_and_fetch(client):
    client, _ = client
    payload = {
        'strategy': 'demo',
        'timestamp': '2024-01-01T00:00:00Z',
        'market': {'symbol': 'AAPL', 'timeframe': '1D'},
        'features': {},
        'risk': {},
        'positions': {},
    }
    resp = client.post('/log_enriched_trade', json=payload)
    assert resp.status_code == 200
    trade_id = resp.json()['id']

    resp2 = client.get('/fetch_payload', params={'id': trade_id})
    assert resp2.status_code == 200
    assert resp2.json()['market']['symbol'] == 'AAPL'


def test_search_docs(client):
    client, _ = client
    resp = client.get('/search_docs', params={'query': 'alpha'})
    assert resp.status_code == 200
    assert resp.json() == [{'id': 1, 'content': 'alpha document'}]


def test_recent_trades(client):
    client, _ = client
    payload = {
        'strategy': 'demo',
        'timestamp': '2024-01-01T00:00:00Z',
        'market': {'symbol': 'AAPL', 'timeframe': '1D'},
        'features': {},
        'risk': {},
        'positions': {},
    }
    client.post('/log_enriched_trade', json=payload)
    resp = client.get('/trades/recent', params={'limit': 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_redis_connectivity():
    import os
    import asyncio
    import redis.asyncio as redis

    url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    async def check():
        r = redis.from_url(url)
        await r.ping()

    try:
        asyncio.run(check())
    except Exception:
        pytest.skip('redis not available')


def test_postgres_connectivity():
    import os
    import asyncio
    import asyncpg

    url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')

    async def check():
        conn = await asyncpg.connect(url)
        await conn.close()

    try:
        asyncio.run(check())
    except Exception:
        pytest.skip('postgres not available')
