import asyncio
import os
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Provide environment variables required at import time
# ---------------------------------------------------------------------------
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("MCP_MEMORY_API_URL", "http://memory.api")

# ---------------------------------------------------------------------------
# Stub out discord.py which is not available in the test environment
# ---------------------------------------------------------------------------
discord_module = types.ModuleType("discord")


class DummyIntents:
    def __init__(self) -> None:
        self.message_content = False

    @classmethod
    def default(cls):  # pragma: no cover - trivial
        return cls()


class DummyBot:
    def __init__(self, *_, **__):
        pass

    def command(self, *_, **__):  # decorator passthrough
        def decorator(func):
            return func

        return decorator

    def event(self, func):  # decorator passthrough
        return func


commands_module = types.ModuleType("commands")
commands_module.Bot = DummyBot
commands_module.Context = object

discord_ext = types.ModuleType("discord.ext")
discord_ext.commands = commands_module

discord_module.Intents = DummyIntents
discord_module.ext = discord_ext

sys.modules.setdefault("discord", discord_module)
sys.modules.setdefault("discord.ext", discord_ext)
sys.modules.setdefault("discord.ext.commands", commands_module)

# Now we can safely import the module under test
import pulse_discord_bot as bot


# ---------------------------------------------------------------------------
# Helper fakes
# ---------------------------------------------------------------------------
class FakeRedis:
    def __init__(self, cached=None):
        self.cached = cached
        self.store = {}

    async def get(self, key):
        return self.cached

    async def set(self, key, value, ex=None):
        self.store[key] = (value, ex)


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):  # pragma: no cover - always ok
        return None

    def json(self):
        return self._data


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        self.called = True
        return self.response


# ---------------------------------------------------------------------------
# fetch_pulse tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fetch_pulse_calls_api_and_caches(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(bot, "_redis", redis)

    client = DummyClient(DummyResponse({"response": "answer"}))
    monkeypatch.setattr(bot.httpx, "AsyncClient", lambda: client)

    recorded = {}

    async def fake_record(payload):
        recorded.update(payload)

    monkeypatch.setattr(bot, "record_interaction", fake_record)

    result = await bot.fetch_pulse("hello")
    await asyncio.sleep(0)  # allow background task to run

    assert result == "answer"
    assert redis.store["pulse:hello"][0] == "answer"
    assert recorded == {"query": "hello", "response": "answer"}
    assert client.called


@pytest.mark.asyncio
async def test_fetch_pulse_cache_hit(monkeypatch):
    redis = FakeRedis(cached="cached-value")
    monkeypatch.setattr(bot, "_redis", redis)

    client = DummyClient(DummyResponse({"response": "miss"}))
    monkeypatch.setattr(bot.httpx, "AsyncClient", lambda: client)

    result = await bot.fetch_pulse("hi")

    assert result == "cached-value"
    assert not client.called


@pytest.mark.asyncio
async def test_fetch_pulse_http_error(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(bot, "_redis", redis)

    import httpx

    class ErrorClient:
        def __init__(self, *args, **kwargs):
            self.called = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):  # pragma: no cover - error path
            self.called = True
            raise httpx.HTTPError("boom")

    monkeypatch.setattr(bot.httpx, "AsyncClient", ErrorClient)

    with pytest.raises(httpx.HTTPError):
        await bot.fetch_pulse("oops")


# ---------------------------------------------------------------------------
# Discord command tests
# ---------------------------------------------------------------------------
class DummyCtx:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


@pytest.mark.asyncio
async def test_pulse_command_sends_result(monkeypatch):
    async def fake_fetch(query):
        return "result"

    monkeypatch.setattr(bot, "fetch_pulse", fake_fetch)

    ctx = DummyCtx()
    await bot.pulse(ctx, query="test")

    assert ctx.sent == ["result"]


@pytest.mark.asyncio
async def test_pulse_command_missing_query():
    ctx = DummyCtx()
    await bot.pulse(ctx, query="")

    assert ctx.sent == ["Usage: !pulse <query>"]


@pytest.mark.asyncio
async def test_pulse_command_handles_error(monkeypatch):
    async def fake_fetch(query):
        raise RuntimeError("fail")

    monkeypatch.setattr(bot, "fetch_pulse", fake_fetch)

    ctx = DummyCtx()
    await bot.pulse(ctx, query="boom")

    assert ctx.sent == ["Error: fail"]


# ---------------------------------------------------------------------------
# /healthz endpoint test
# ---------------------------------------------------------------------------
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


@pytest.mark.asyncio
async def test_health_endpoint():
    app = web.Application()
    app.router.add_get("/healthz", bot.health)

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    resp = await client.get("/healthz")
    assert resp.status == 200
    assert await resp.json() == {"status": "ok"}

    await client.close()

