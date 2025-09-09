import os
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import django
from django.test import Client
import pytest

# Setup Django environment similar to other tests
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "django"))
sys.path.insert(0, str(ROOT))

app_stub = types.ModuleType("app")
app_stub.__path__ = [str(ROOT / "backend" / "django" / "app")]
sys.modules.setdefault("app", app_stub)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.django.app.test_settings")
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")


@pytest.fixture
def client():
    return Client()


def _mock_response(data):
    m = Mock()
    m.json.return_value = data
    m.status_code = 200
    m.raise_for_status = lambda: None
    return m


def test_history_deals_proxy_returns_upstream(monkeypatch, client):
    data = {"items": [1, 2]}
    monkeypatch.setenv("MT5_API_URL", "http://mt5.test")
    calls = {}

    def fake_get(url, params=None, timeout=None):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return _mock_response(data)

    monkeypatch.setattr("app.nexus.views.requests.get", fake_get)
    resp = client.get("/api/v1/history_deals_get", {"login": "1"})
    assert resp.status_code == 200
    assert resp.json() == data
    assert calls["url"] == "http://mt5.test/history_deals_get"
    assert calls["params"]["login"] == "1"


def test_history_orders_proxy_returns_upstream(monkeypatch, client):
    data = {"orders": [3]}
    monkeypatch.setenv("MT5_API_URL", "http://mt5.test")
    calls = {}

    def fake_get(url, params=None, timeout=None):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return _mock_response(data)

    monkeypatch.setattr("app.nexus.views.requests.get", fake_get)
    resp = client.get("/api/v1/history_orders_get", {"login": "1"})
    assert resp.status_code == 200
    assert resp.json() == data
    assert calls["url"] == "http://mt5.test/history_orders_get"
    assert calls["params"]["login"] == "1"
