import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

TEST_KEY = "test-key"


@pytest.fixture
def app_client(monkeypatch):

    monkeypatch.setenv("MCP2_API_KEY", TEST_KEY)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
    )
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


BASE_FIELDS = {
    "strategy": "test",
    "symbol": "AAPL",
    "timeframe": "1D",
    "date": "2024-01-01T00:00:00Z",
}


def test_health(app_client):
    client, _, _, _ = app_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_requires_api_key_header(app_client):
    client, _, _, _ = app_client
    resp = client.post("/mcp/tools/search", json={"query": "hammer", **BASE_FIELDS})
    assert resp.status_code == 401


def test_tools_search_cache_hit(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    query = "hammer"
    cached = mcp2.ToolSearchResponse(
        results=[mcp2.ToolInfo(id=1, name="Hammer", description="useful")],
        payload=mcp2.BasePayload(**BASE_FIELDS),
    )
    fake_redis.store[f"toolsearch:{query}"] = cached.model_dump_json()

    resp = client.post(
        "/mcp/tools/search",
        json={"query": query, **BASE_FIELDS},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    fake_pool.fetch.assert_not_called()
    assert fake_redis.get.await_count == 1
    assert resp.json() == cached.model_dump(mode="json")


def test_tools_search_db_fallback(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    query = "saw"
    fake_pool.fetch.return_value = [
        {"id": 2, "name": "Saw", "description": "cutting"}
    ]

    resp = client.post(
        "/mcp/tools/search",
        json={"query": query, **BASE_FIELDS},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    assert fake_pool.fetch.await_count == 1
    assert fake_redis.set.await_count == 1

    expected = mcp2.ToolSearchResponse(
        results=[mcp2.ToolInfo(id=2, name="Saw", description="cutting")],
        payload=mcp2.BasePayload(**BASE_FIELDS),
    )
    assert resp.json() == expected.model_dump(mode="json")
    assert (
        fake_redis.store[f"toolsearch:{query}"] == expected.model_dump_json()
    )


def test_tools_fetch_cache_hit(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    tool = mcp2.ToolInfo(id=1, name="Hammer", description="useful", content="full")
    fake_redis.store["tool:1"] = tool.model_dump_json()

    resp = client.post(
        "/mcp/tools/fetch",
        json={"ids": [1], **BASE_FIELDS},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    fake_pool.fetch.assert_not_called()
    payload_dict = mcp2.BasePayload(**BASE_FIELDS).model_dump(mode="json")
    assert resp.json() == {
        "tools": [tool.model_dump(mode="json")],
        "payload": payload_dict,
    }


def test_tools_fetch_db_fallback(app_client):
    client, fake_redis, fake_pool, mcp2 = app_client
    fake_pool.fetch.return_value = [
        {"id": 2, "name": "Saw", "description": "cut", "content": "full"}
    ]

    resp = client.post(
        "/mcp/tools/fetch",
        json={"ids": [2], **BASE_FIELDS},
        headers={"X-API-Key": TEST_KEY},
    )

    assert resp.status_code == 200
    assert fake_pool.fetch.await_count == 1
    assert fake_redis.set.await_count == 1

    expected_tool = mcp2.ToolInfo(
        id=2, name="Saw", description="cut", content="full"
    )
    payload_dict = mcp2.BasePayload(**BASE_FIELDS).model_dump(mode="json")
    assert resp.json() == {
        "tools": [expected_tool.model_dump(mode="json")],
        "payload": payload_dict,
    }
    assert fake_redis.store["tool:2"] == expected_tool.model_dump_json()


def test_payload_validation(app_client):
    client, _, _, _ = app_client
    bad_payload = {
        "query": "hammer",
        "symbol": "AAPL",
        "timeframe": "1D",
        "date": "2024-01-01T00:00:00Z",
    }
    resp = client.post(
        "/mcp/tools/search",
        json=bad_payload,
        headers={"X-API-Key": TEST_KEY},
    )
    assert resp.status_code == 422
