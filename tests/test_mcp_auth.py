import json
import httpx
from fastapi.testclient import TestClient
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import backend.mcp.mcp_server as mcp_server

TEST_KEY = "test-key"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MCP_API_KEY", TEST_KEY)
    return TestClient(mcp_server.app)


def test_mcp_public(monkeypatch, client):
    async def finite_stream():
        yield "open\n"

    monkeypatch.setattr(mcp_server, "generate_mcp_stream", finite_stream)

    response = client.get("/mcp")
    assert response.status_code == 200


def test_exec_requires_api_key(client):
    assert client.get("/exec/foo").status_code == 401
    assert (
        client.get("/exec/foo", headers={"X-API-Key": "wrong"}).status_code == 401
    )
    assert (
        client.get(
            "/exec/foo", headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )


def _mock_response():
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "application/json"}
            self._data = {"ok": True}
            self.text = json.dumps(self._data)

        def json(self):
            return self._data

    return MockResponse()


def test_exec_with_valid_x_api_key(client, monkeypatch):
    async def mock_request(self, *args, **kwargs):
        return _mock_response()

    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    response = client.get("/exec/foo", headers={"X-API-Key": TEST_KEY})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_exec_with_valid_bearer_token(client, monkeypatch):
    async def mock_request(self, *args, **kwargs):
        return _mock_response()

    monkeypatch.setattr(httpx.AsyncClient, "request", mock_request)

    response = client.get(
        "/exec/foo", headers={"Authorization": f"Bearer {TEST_KEY}"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_no_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
