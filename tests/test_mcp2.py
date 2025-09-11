import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

TEST_KEY = "test-key"


@pytest.fixture
def app_client(monkeypatch):
    monkeypatch.setenv("MCP2_API_KEY", TEST_KEY)
    import services.mcp2.mcp2_server as mcp2_server
    importlib.reload(mcp2_server)

    class FakeRedis:
        def __init__(self):
            self.store = {}
            self.get = AsyncMock(side_effect=self._get)
            self.set = AsyncMock(side_effect=self._set)
            self.close = AsyncMock()

        async def _get(self, key):
            return self.store.get(key)

        async def _set(self, key, value, ex=None):
            self.store[key] = value

    fake_redis = FakeRedis()
    fake_pool = SimpleNamespace(fetch=AsyncMock(), close=AsyncMock())

    monkeypatch.setattr(mcp2_server, "redis_client", fake_redis)
    monkeypatch.setattr(mcp2_server, "pg_pool", fake_pool)
    monkeypatch.setattr(
        mcp2_server.asyncpg, "create_pool", AsyncMock(return_value=fake_pool)
    )

    client = TestClient(mcp2_server.app)
    return client, fake_redis, fake_pool, mcp2_server


def test_health(app_client):
    client, _, _, _ = app_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tools_search_cache_hit(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    query = "hammer"
    cached = mcp2.ToolSearchResponse(
        results=[mcp2.ToolInfo(id=1, name="Hammer", description="useful")]
    )
    fake_redis.store[f"toolsearch:{query}"] = cached.model_dump_json()

    resp = client.post(
        "/mcp/tools/search",
        json={"query": query},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    fake_pool.fetch.assert_not_called()
    assert fake_redis.get.await_count == 1
    assert resp.json() == cached.model_dump()


def test_tools_search_db_fallback(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    query = "saw"
    fake_pool.fetch.return_value = [
        {"id": 2, "name": "Saw", "description": "cutting"}
    ]

    resp = client.post(
        "/mcp/tools/search",
        json={"query": query},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    assert fake_pool.fetch.await_count == 1
    assert fake_redis.set.await_count == 1

    expected = mcp2.ToolSearchResponse(
        results=[mcp2.ToolInfo(id=2, name="Saw", description="cutting")]
    )
    assert resp.json() == expected.model_dump()
    assert fake_redis.store[f"toolsearch:{query}"] == expected.model_dump_json()


def test_tools_fetch_cache_hit(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    tool = mcp2.ToolInfo(id=1, name="Hammer", description="useful", content="full")
    fake_redis.store["tool:1"] = tool.model_dump_json()

    resp = client.post(
        "/mcp/tools/fetch",
        json={"ids": [1]},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    fake_pool.fetch.assert_not_called()
    assert resp.json() == {"tools": [tool.model_dump()]}


def test_tools_fetch_db_fallback(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    fake_pool.fetch.return_value = [
        {"id": 2, "name": "Saw", "description": "cut", "content": "full"}
    ]

    resp = client.post(
        "/mcp/tools/fetch",
        json={"ids": [2]},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    assert fake_pool.fetch.await_count == 1
    assert fake_redis.set.await_count == 1

    expected_tool = mcp2.ToolInfo(
        id=2, name="Saw", description="cut", content="full"
    )
    assert resp.json() == {"tools": [expected_tool.model_dump()]}
    assert fake_redis.store["tool:2"] == expected_tool.model_dump_json()
