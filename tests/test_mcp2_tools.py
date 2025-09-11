import os
import json
import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.mcp2.routers.tools import search_docs, fetch_payload
from services.mcp2.storage import redis_client


@pytest.fixture
def client(monkeypatch):
    base = os.getenv("MCP2_BASE")
    if base:
        c = httpx.Client(base_url=base)
        try:
            yield c, None
        finally:
            c.close()
    else:
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

        app = FastAPI()
        app.add_api_route('/mcp/tools/search', search_docs, methods=['GET'])
        app.add_api_route('/mcp/tools/fetch', fetch_payload, methods=['GET'])

        yield TestClient(app), fake_redis


def test_tools_search(client):
    client, _ = client
    resp = client.get('/mcp/tools/search', params={'query': 'alpha'})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data and 'id' in data[0] and 'content' in data[0]


def test_tools_fetch(client):
    client, fake_redis = client
    if fake_redis is None:
        pytest.skip('external MCP2 base not seeded')
    trade_id = '123'
    payload = {
        'strategy': 'demo',
        'timestamp': '2024-01-01T00:00:00Z',
        'market': {'symbol': 'AAPL', 'timeframe': '1D'},
        'features': {},
        'risk': {},
        'positions': {},
    }
    fake_redis.kv[redis_client.ns(f'payload:{trade_id}')] = json.dumps(payload)
    resp = client.get('/mcp/tools/fetch', params={'id': trade_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data['market']['symbol'] == 'AAPL'
    assert data['strategy'] == 'demo'
