import httpx
from fastapi.testclient import TestClient
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import backend.mcp.mcp_server as mcp_server

client = TestClient(mcp_server.app)
TEST_KEY = "test-key"


def setup_api_key(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", TEST_KEY)


def test_exec_action_open_success(monkeypatch):
    setup_api_key(monkeypatch)

    class MockResponse:
        status_code = 200
        text = json.dumps({"ok": True})

        def json(self):
            return {"ok": True}

    async def mock_post(self, url, json):
        assert url.endswith("/trade/open")
        assert json["symbol"] == "XAUUSD"
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    payload = {
        "type": "position_open",
        "payload": {"symbol": "XAUUSD", "side": "buy", "volume": 0.1},
    }
    resp = client.post("/exec", json=payload, headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_exec_action_unsupported(monkeypatch):
    setup_api_key(monkeypatch)
    payload = {"type": "unknown", "payload": {}}
    resp = client.post("/exec", json=payload, headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 400


def test_search_tool_success(monkeypatch):
    setup_api_key(monkeypatch)

    class MockResponse:
        status_code = 200

        def json(self):
            return {"symbols": ["XAUUSD", "EURUSD", "GBPJPY"]}

    async def mock_get(self, url):
        assert url.endswith("/market/symbols")
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    resp = client.post("/tool/search", params={"query": "usd"}, headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 200
    assert resp.json() == {"results": ["XAUUSD", "EURUSD"]}


def test_search_tool_api_error(monkeypatch):
    setup_api_key(monkeypatch)

    async def mock_get(self, url):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    resp = client.post("/tool/search", params={"query": "usd"}, headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 502
