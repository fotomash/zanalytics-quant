from types import SimpleNamespace
import importlib
import sys

import pytest


@pytest.fixture
def pulse_bot(monkeypatch):
    from discord.ext import commands

    original_bot = commands.Bot

    def patched_bot(*args, **kwargs):
        kwargs.setdefault("help_command", None)
        return original_bot(*args, **kwargs)

    monkeypatch.setattr(commands, "Bot", patched_bot)
    sys.modules.pop("services.pulse_bot.bot", None)
    return importlib.import_module("services.pulse_bot.bot")


class DummyCtx:
    def __init__(self, channel_id: int):
        self.channel = SimpleNamespace(id=channel_id)
        self.sent: list[str] = []

    async def send(self, message: str):
        self.sent.append(message)


class FakeRedis:
    def __init__(self, data=None, fail=False):
        self.data = data or {}
        self.fail = fail
        self.setex_called_with = None

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.setex_called_with = (key, ttl, value)
        if self.fail:
            raise RuntimeError("boom")
        self.data[key] = value


@pytest.mark.anyio("asyncio")
async def test_cmd_help_authorization(monkeypatch, pulse_bot):
    bot = pulse_bot
    monkeypatch.setattr(bot, "CHANNEL_WHITELIST", {"1"})

    ctx = DummyCtx(channel_id=2)
    await bot.cmd_help(ctx)
    assert ctx.sent == []

    ctx_ok = DummyCtx(channel_id=1)
    await bot.cmd_help(ctx_ok)
    assert ctx_ok.sent  # message should be sent


@pytest.mark.anyio("asyncio")
async def test_cached_response_cache_hit(monkeypatch, pulse_bot):
    bot = pulse_bot
    redis = FakeRedis({"prompt:hi": "cached"})
    monkeypatch.setattr(bot, "redis_client", redis)

    called = {}

    def fake_recall(prompt):
        called["recall"] = True
        return ["mem"]

    def fake_store(prompt, response):
        called["store"] = True

    monkeypatch.setattr(bot, "_recall", fake_recall)
    monkeypatch.setattr(bot, "_store", fake_store)

    result = await bot._cached_response("hi")
    assert result == "cached"
    assert "recall" not in called
    assert "store" not in called
    assert redis.setex_called_with is None


@pytest.mark.anyio("asyncio")
async def test_cached_response_cache_miss(monkeypatch, pulse_bot):
    bot = pulse_bot
    redis = FakeRedis()
    monkeypatch.setattr(bot, "redis_client", redis)

    recalled = []
    stored = []

    def fake_recall(prompt):
        recalled.append(prompt)
        return ["m1", "m2"]

    def fake_store(prompt, response):
        stored.append((prompt, response))

    monkeypatch.setattr(bot, "_recall", fake_recall)
    monkeypatch.setattr(bot, "_store", fake_store)

    result = await bot._cached_response("hello")
    assert result == "hello\nm1\nm2"
    assert recalled == ["hello"]
    assert stored == [("hello", "hello\nm1\nm2")]
    assert redis.setex_called_with == ("prompt:hello", 3600, "hello\nm1\nm2")


@pytest.mark.anyio("asyncio")
async def test_cached_response_redis_error(monkeypatch, pulse_bot):
    bot = pulse_bot
    redis = FakeRedis(fail=True)
    monkeypatch.setattr(bot, "redis_client", redis)

    monkeypatch.setattr(bot, "_recall", lambda prompt: [])
    monkeypatch.setattr(bot, "_store", lambda prompt, response: None)

    result = await bot._cached_response("oops")
    assert result == "oops"
    # even though setex fails, function should return response without raising
    assert redis.setex_called_with == ("prompt:oops", 3600, "oops")
