import importlib

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture()
def bot(monkeypatch):
    import discord.ext.commands.bot as dcbot
    orig_init = dcbot.Bot.__init__

    def patched_init(self, *args, **kwargs):
        kwargs.setdefault("help_command", None)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(dcbot.Bot, "__init__", patched_init)
    module = importlib.reload(importlib.import_module("services.pulse_bot.bot"))
    return module


@pytest.mark.asyncio
async def test_cmd_help_authorization(monkeypatch, bot):
    ctx = MagicMock()
    ctx.channel.id = 123
    ctx.send = AsyncMock()

    # Authorized channel
    monkeypatch.setattr(bot, "CHANNEL_WHITELIST", {"123"})
    await bot.cmd_help(ctx)
    ctx.send.assert_called_once()

    # Unauthorized channel
    ctx2 = MagicMock()
    ctx2.channel.id = 999
    ctx2.send = AsyncMock()
    await bot.cmd_help(ctx2)
    ctx2.send.assert_not_called()


@pytest.mark.asyncio
async def test_cached_response_hits_and_misses(monkeypatch, bot):
    redis = MagicMock()
    redis.get.return_value = "cached"
    redis.setex = MagicMock()
    monkeypatch.setattr(bot, "redis_client", redis)

    recall = MagicMock()
    store = MagicMock()
    monkeypatch.setattr(bot, "_recall", recall)
    monkeypatch.setattr(bot, "_store", store)

    # Cache hit
    result = await bot._cached_response("hello")
    assert result == "cached"
    recall.assert_not_called()
    store.assert_not_called()
    redis.setex.assert_not_called()

    # Cache miss with memories
    redis.get.return_value = None
    recall.return_value = ["m1", "m2"]
    result2 = await bot._cached_response("hello")
    assert result2 == "hello\nm1\nm2"
    recall.assert_called_with("hello")
    store.assert_called_once_with("hello", result2)
    redis.setex.assert_called_once_with("prompt:hello", 3600, result2)


@pytest.mark.asyncio
async def test_cached_response_handles_redis_errors(monkeypatch, bot):
    redis = MagicMock()
    redis.get.return_value = None
    redis.setex.side_effect = Exception("boom")
    monkeypatch.setattr(bot, "redis_client", redis)
    monkeypatch.setattr(bot, "_recall", MagicMock(return_value=[]))
    monkeypatch.setattr(bot, "_store", MagicMock())

    result = await bot._cached_response("hi")
    assert result == "hi"
    redis.setex.assert_called_once()


def test_recall_handles_request_errors(monkeypatch, bot):
    monkeypatch.setattr(bot, "MCP_MEMORY_API_URL", "http://memory")
    monkeypatch.setattr(bot, "MCP_MEMORY_API_KEY", "key")
    with patch.object(bot.requests, "post", side_effect=Exception("fail")) as post:
        memories = bot._recall("prompt")
    assert memories == []
    post.assert_called_once()
