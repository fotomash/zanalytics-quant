import json
import logging
import asyncio

import services.mcp2.routers.echonudge as echonudge


def test_call_ollama_logs_warning(monkeypatch, caplog):
    async def boom_post(self, url, json, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(echonudge.httpx.AsyncClient, "post", boom_post)
    with caplog.at_level(logging.WARNING):
        resp = asyncio.run(echonudge._call_ollama("hi"))
    assert any("Ollama call failed" in r.message for r in caplog.records)
    assert json.loads(resp)["reason"] == "offline stub"
