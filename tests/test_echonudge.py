import asyncio
import json
from unittest.mock import AsyncMock

from services.mcp2.routers import echonudge as en


def test_echonudge_publishes_on_alert(monkeypatch):
    """EchoNudge publishes an alert when model signals it."""

    async def run() -> None:
        fake_resp = {"label": "alert", "priority": "high", "action": "none", "reason": "test"}

        async def fake_call(prompt: str) -> str:  # noqa: D401
            return json.dumps(fake_resp)

        monkeypatch.setattr(en, "_call_ollama", fake_call)

        publish = AsyncMock(return_value=1)
        monkeypatch.setattr(en.redis_client.redis, "publish", publish)

        req = en.EchoNudgeRequest(prompt="hello")
        resp = await en.echonudge(req)

        assert resp.result == fake_resp
        assert resp.published is True
        publish.assert_awaited_once()

    asyncio.run(run())


def test_echonudge_no_publish(monkeypatch):
    """No publish when model does not request alert or hedge."""

    async def run() -> None:
        fake_resp = {"label": "hold", "priority": "low", "action": "wait", "reason": "test"}

        async def fake_call(prompt: str) -> str:
            return json.dumps(fake_resp)

        monkeypatch.setattr(en, "_call_ollama", fake_call)

        publish = AsyncMock(return_value=1)
        monkeypatch.setattr(en.redis_client.redis, "publish", publish)

        req = en.EchoNudgeRequest(prompt="hello")
        resp = await en.echonudge(req)

        assert resp.result == fake_resp
        assert resp.published is False
        publish.assert_not_called()

    asyncio.run(run())
