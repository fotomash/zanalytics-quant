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


def test_positions_proxy_uses_api_url(monkeypatch, client):
    data = [{"symbol": "EURUSD"}]
    monkeypatch.setenv("MT5_API_URL", "http://mt5.test")
    monkeypatch.delenv("MT5_URL", raising=False)
    calls = {}

    def fake_get(url, timeout=None):
        calls["url"] = url
        calls["timeout"] = timeout
        return _mock_response(data)

    monkeypatch.setattr("app.nexus.views.requests.get", fake_get)
    resp = client.get("/api/v1/account/positions")
    assert resp.status_code == 200
    assert resp.json() == data
    assert calls["url"] == "http://mt5.test/positions_get"


def test_account_info_uses_api_url(monkeypatch, client):
    data = {"equity": 1000}
    monkeypatch.setenv("MT5_API_URL", "http://mt5.test")
    monkeypatch.delenv("MT5_URL", raising=False)
    calls = {}

    def fake_get(url, timeout=None):
        calls["url"] = url
        calls["timeout"] = timeout
        return _mock_response(data)

    monkeypatch.setattr("app.nexus.views.requests.get", fake_get)
    resp = client.get("/api/v1/account/info")
    assert resp.status_code == 200
    assert resp.json()["equity"] == 1000
    assert calls["url"] == "http://mt5.test/account_info"
