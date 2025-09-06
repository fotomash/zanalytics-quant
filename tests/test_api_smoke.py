import asyncio
import httpx
from httpx import ASGITransport
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.main import app


async def _call(method, url, **kw):
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kw)


def test_health():
    r = asyncio.run(_call("GET", "/pulse/health"))
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_score_minimal():
    r = asyncio.run(_call("POST", "/pulse/score", json={"symbol": "EURUSD"}))
    assert r.status_code == 200
    body = r.json()
    assert "score" in body and "grade" in body

