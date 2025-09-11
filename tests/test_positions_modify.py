import os
import asyncio
import time
import sys
from pathlib import Path
from httpx import ASGITransport, AsyncClient

# Django requires a secret key even for tests
os.environ.setdefault("DJANGO_SECRET_KEY", "test-key")
os.environ.setdefault("DJANGO_DOMAIN", "test")

# Ensure Django project is importable (ahead of top-level `app` package)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "django"))

from app.asgi import application
import bridge.mt5 as mt5_bridge
import app.nexus.journal_service as journal_service


class DummyResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = ""

    def json(self):
        return self._data


def test_positions_modify_returns_quickly(monkeypatch):
    ticket = 123

    from types import SimpleNamespace

    def fake_get(url, timeout):
        return DummyResp([{ "ticket": ticket, "symbol": "EURUSD" }])

    def fake_post(url, json, timeout):
        assert "/api/v1/orders/modify" not in url
        return DummyResp({"ok": True, "result": {"ticket": ticket}})

    fake_requests = SimpleNamespace(get=fake_get, post=fake_post)
    monkeypatch.setattr(mt5_bridge, "requests", fake_requests)
    monkeypatch.setattr(journal_service, "requests", SimpleNamespace(post=lambda *a, **k: DummyResp({})))

    transport = ASGITransport(app=application)

    async def _run():
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.time()
            resp = await client.post(f"/api/v1/positions/{ticket}/modify", json={"sl": 1.234})
            return resp, time.time() - start

    response, duration = asyncio.run(_run())
    assert response.status_code == 200
    assert response.json().get("ok") is True
    assert duration < 1.0
