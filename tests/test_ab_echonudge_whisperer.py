import asyncio
import json
from unittest.mock import AsyncMock

from services.mcp2.routers import ab as abmod


def test_ab_publishes_on_conflict(monkeypatch):
    """Conflict between EchoNudge and Whisperer publishes alert."""

    async def run() -> None:
        en_resp = {"label": "buy", "priority": "low", "action": "none", "reason": "test"}
        wh_resp = {"label": "sell", "priority": "low", "action": "none", "reason": "test"}

        async def fake_en(prompt: str) -> str:
            return json.dumps(en_resp)

        async def fake_wh(prompt: str) -> str:
            return json.dumps(wh_resp)

        monkeypatch.setattr(abmod, "_call_ollama", fake_en)
        monkeypatch.setattr(abmod, "_call_openai", fake_wh)

        publish = AsyncMock(return_value=1)
        monkeypatch.setattr(abmod.redis_client.redis, "publish", publish)

        body = abmod.ABRequest(prompt="hi", publish_on_conflict=True)
        resp = await abmod.ab_echonudge_whisperer(body)

        assert resp.echonudge == en_resp
        assert resp.whisperer == wh_resp
        assert resp.conflict is True
        assert resp.published is True
        publish.assert_awaited_once()

    asyncio.run(run())


def test_ab_no_publish_without_conflict(monkeypatch):
    """No publish when EchoNudge and Whisperer agree."""

    async def run() -> None:
        en_resp = {"label": "buy", "priority": "low", "action": "none", "reason": "test"}
        wh_resp = {"label": "buy", "priority": "low", "action": "none", "reason": "test"}

        async def fake_en(prompt: str) -> str:
            return json.dumps(en_resp)

        async def fake_wh(prompt: str) -> str:
            return json.dumps(wh_resp)

        monkeypatch.setattr(abmod, "_call_ollama", fake_en)
        monkeypatch.setattr(abmod, "_call_openai", fake_wh)

        publish = AsyncMock(return_value=1)
        monkeypatch.setattr(abmod.redis_client.redis, "publish", publish)

        body = abmod.ABRequest(prompt="hi", publish_on_conflict=True)
        resp = await abmod.ab_echonudge_whisperer(body)

        assert resp.conflict is False
        assert resp.published is False
        publish.assert_not_called()

    asyncio.run(run())
