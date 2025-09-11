import os
import importlib
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient


def _api_key() -> str:
    return os.getenv("MCP_API_KEY", "test-key")


@pytest.fixture
def client(monkeypatch):
    key = _api_key()
    monkeypatch.setenv("MCP_API_KEY", key)
    base = os.getenv("MCP1_BASE")
    if base:
        c = httpx.Client(base_url=base)
        try:
            yield c
        finally:
            c.close()
    else:
        import sys
        sys.modules.setdefault("mt5_adapter", SimpleNamespace(init_mt5=lambda: None))
        mt5 = sys.modules.setdefault("MetaTrader5", SimpleNamespace())
        mt5.orders_get = lambda **kwargs: [
            SimpleNamespace(
                ticket=1,
                symbol="XAUUSD",
                type=0,
                volume=1.0,
                price_open=1.0,
                time_setup=0,
            )
        ]
        mcp_server = importlib.import_module("backend.mcp.mcp_server")
        yield TestClient(mcp_server.app)


def _headers():
    return {"X-API-Key": _api_key()}


def test_health(client):
    resp = client.get("/health", headers=_headers())
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_session_boot(client):
    resp = client.post(
        "/api/v1/actions/query",
        json={"type": "session_boot"},
        headers=_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trades" in data
    assert "positions" in data


def test_positions_list(client):
    resp = client.post(
        "/api/v1/actions/query",
        json={"type": "account_positions"},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_trades_recent(client):
    resp = client.post(
        "/api/v1/actions/query",
        json={"type": "trades_recent"},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
