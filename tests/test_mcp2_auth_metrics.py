import json
import os

import pytest
from fastapi.testclient import TestClient

from services.mcp2.app import app

TEST_KEY = "test-key"


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
        "services.mcp2.storage.redis_client.redis", fake_redis
    )

    class FakePool:
        async def fetch(self, query, *args):
            return []

    async def fake_get_pool():
        return FakePool()

    monkeypatch.setattr("services.mcp2.storage.pg.get_pool", fake_get_pool)
    monkeypatch.setattr("services.mcp2.routers.tools.get_pool", fake_get_pool)

    monkeypatch.setenv("MCP2_API_KEY", TEST_KEY)
    return TestClient(app)


def test_endpoint_requires_api_key(client):
    resp = client.get("/search_docs", params={"query": "alpha"})
    assert resp.status_code == 401
    resp = client.get(
        "/search_docs", params={"query": "alpha"}, headers={"X-API-Key": "wrong"}
    )
    assert resp.status_code == 401


def test_endpoint_accepts_valid_key(client):
    resp = client.get(
        "/search_docs", params={"query": "alpha"}, headers={"X-API-Key": TEST_KEY}
    )
    assert resp.status_code == 200


def test_metrics_endpoint(client):
    # generate a request to increment counter
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "mcp2_requests_total" in resp.text
