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

# Ensure real pandas is available for enrichment
sys.modules.pop("pandas", None)
import pandas as pd
pulse_service = importlib.import_module("app.nexus.pulse.service")
pulse_views = importlib.import_module("app.nexus.pulse.views")
importlib.reload(pulse_service)
importlib.reload(pulse_views)


@pytest.fixture
def client():
    return Client()


def _sample_loader(symbol):
    dates = pd.date_range("2023-01-01", periods=60, freq="T")
    base = {
        "timestamp": dates,
        "open": range(60),
        "high": range(1, 61),
        "low": range(0, 60),
        "close": range(1, 61),
        "volume": [100] * 60,
    }
    df = pd.DataFrame(base)
    return {"M15": df, "M1": df, "H1": df, "H4": df}


def test_bars_enriched_with_enrichment(client, monkeypatch):
    monkeypatch.setattr(pulse_service, "_load_minute_data", _sample_loader)
    monkeypatch.setattr(pulse_views, "_load_minute_data", _sample_loader)
    response = client.get(
        "/api/v1/feed/bars-enriched",
        {"symbol": "EURUSD", "timeframe": "M15", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["items"][-1]["sma20"] is not None


def test_bars_enriched_without_enrichment(client, monkeypatch):
    monkeypatch.setattr(pulse_service, "_load_minute_data", _sample_loader)
    monkeypatch.setattr(pulse_views, "_load_minute_data", _sample_loader)
    response = client.get(
        "/api/v1/feed/bars-enriched",
        {"symbol": "EURUSD", "timeframe": "M15", "limit": 5, "enrich": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["items"][-1]["sma20"] is None


def test_bars_enriched_missing_pandas(client, monkeypatch):
    def _broken_loader(symbol):
        raise ImportError("pandas missing")

    monkeypatch.setattr(pulse_service, "_load_minute_data", _broken_loader)
    monkeypatch.setattr(pulse_views, "_load_minute_data", _broken_loader)
    response = client.get(
        "/api/v1/feed/bars-enriched",
        {"symbol": "EURUSD", "timeframe": "M15"},
    )
    assert response.status_code == 503
    assert "pandas" in response.json().get("error", "")

