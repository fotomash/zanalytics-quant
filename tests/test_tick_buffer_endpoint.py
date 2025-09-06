import os
import json
import sys
from pathlib import Path
import django
from django.test import Client
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "django"))
sys.path.insert(0, str(ROOT))
import types
app_stub = types.ModuleType("app")
app_stub.__path__ = [str(ROOT / "backend" / "django" / "app")]
sys.modules['app'] = app_stub
os.environ["DJANGO_SETTINGS_MODULE"] = "backend.django.app.test_settings"
django.setup()
from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")

import pulse_api.views as pulse_views


class DummyRedis:
    def __init__(self):
        self.store = {}

    def rpush(self, key, *values):
        self.store.setdefault(key, []).extend(values)

    def lrange(self, key, start, end):
        data = self.store.get(key, [])
        if start < 0:
            start = max(len(data) + start, 0)
        if end == -1:
            end = len(data) - 1
        return data[start : end + 1]


@pytest.fixture
def client(monkeypatch):
    fake = DummyRedis()
    monkeypatch.setattr(pulse_views, "redis_client", fake)
    return Client(), fake


def test_tick_buffer_returns_latest_ticks(client):
    client, redis_client = client
    key = "ticks:EURUSD:live"
    redis_client.rpush(key, json.dumps({"price": 1.1}), json.dumps({"price": 1.2}))

    response = client.get("/api/ticks/buffer", {"symbol": "EURUSD"})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EURUSD"
    assert len(data["ticks"]) == 2
    assert data["ticks"][0]["price"] == 1.1
