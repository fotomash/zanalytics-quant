import os
import json
import httpx
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import backend.mcp.mcp_server as mcp_server

client = TestClient(mcp_server.app)

TEST_KEY = "test-key"


def test_mcp_public(monkeypatch):
    async def finite_stream():
        yield "open\n"

    monkeypatch.setattr(mcp_server, "generate_mcp_stream", finite_stream)

    response = client.get("/mcp")
    assert response.status_code == 200


def test_exec_requires_api_key():
    assert client.get("/exec/foo").status_code == 401
    assert client.get("/exec/foo", headers={"X-API-Key": "wrong"}).status_code == 401


def test_exec_with_valid_api_key(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", TEST_KEY)
    monkeypatch.setattr(mcp_server, "API_KEY", TEST_KEY)

    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "application/json"}
            self._data = {"ok": True}
            self.text = json.dumps(self._data)

        def json(self):
            return self._data

    async def mock_request(self, *args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    response = client.get("/exec/foo", headers={"X-API-Key": TEST_KEY})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
