import os
import sys
from pathlib import Path
import types
import importlib
import django
from django.test import Client
import pytest

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

pulse_service = importlib.import_module("app.nexus.pulse.service")
pulse_views = importlib.import_module("app.nexus.pulse.views")
importlib.reload(pulse_service)
importlib.reload(pulse_views)


@pytest.fixture
def client():
    return Client()


def _broken_loader(symbol):
    raise ImportError("minute data unavailable")


def test_pulse_detail_missing_minute_data(client, monkeypatch):
    monkeypatch.setattr(pulse_service, "_load_minute_data", _broken_loader)
    monkeypatch.setattr(pulse_views, "_load_minute_data", _broken_loader)
    response = client.get("/api/v1/feed/pulse-detail", {"symbol": "EURUSD"})
    assert response.status_code == 503
    assert "minute data unavailable" in response.json().get("error", "")
