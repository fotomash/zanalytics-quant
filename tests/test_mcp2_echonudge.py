import logging

import pytest

from services.mcp2.routers import echonudge


@pytest.mark.asyncio
async def test_publish_failure_logs_and_counts(monkeypatch, caplog):
    async def boom(channel: str, message: str) -> None:  # pragma: no cover - simulated
        raise RuntimeError("redis down")

    monkeypatch.setattr(echonudge.redis_client.redis, "publish", boom)
    echonudge.ECHONUDGE_PUBLISH_FAILURES._value.set(0)

    result = {"label": "alert", "action": "none"}

    with caplog.at_level(logging.ERROR):
        published = await echonudge._maybe_publish_alert(result, "p", None)

    assert not published
    assert "EchoNudge alert publish failed" in caplog.text
    assert echonudge.ECHONUDGE_PUBLISH_FAILURES._value.get() == 1

