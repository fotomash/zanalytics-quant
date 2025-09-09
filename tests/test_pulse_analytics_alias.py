import os
import sys
import types
from pathlib import Path

import django
from django.conf import settings
from django.test import Client
from rest_framework.response import Response


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "django"))
sys.path.insert(0, str(ROOT))

# Provide a minimal ``app`` package so Django can resolve modules
app_stub = types.ModuleType("app")
app_stub.__path__ = [str(ROOT / "backend" / "django" / "app")]
sys.modules["app"] = app_stub

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.django.app.test_settings")
django.setup()

settings.ALLOWED_HOSTS.append("testserver")


def test_pulse_analytics_alias_route(monkeypatch):
    from app.nexus.pulse import views as pulse_views

    def fake_get(self, request):
        return Response({"labels": [], "counts": []})

    monkeypatch.setattr(pulse_views.TradesQuality, "get", fake_get)

    client = Client()
    resp = client.get("/api/pulse/analytics/trades/quality")
    assert resp.status_code == 200
    body = resp.json()
    assert "labels" in body and "counts" in body

