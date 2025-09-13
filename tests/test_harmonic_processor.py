import asyncio
import pytest
import sys
import types

sys.modules.setdefault("talib", types.ModuleType("talib"))
qdrant_stub = types.ModuleType("qdrant_client")
qdrant_stub.models = types.SimpleNamespace(PointStruct=lambda **kwargs: None)
sys.modules.setdefault("qdrant_client", qdrant_stub)

from utils.processors.harmonic import HarmonicProcessor


class DummySyncClient:
    def __init__(self):
        self.called = False

    def upsert(self, **kwargs):
        self.called = True


class DummyAsyncClient:
    def __init__(self):
        self.called = False

    async def upsert(self, **kwargs):
        self.called = True


def test_upsert_uses_background_thread_for_sync_client():
    async def run():
        client = DummySyncClient()
        proc = HarmonicProcessor(client)
        await proc.upsert([[0.1]], [{}], [1])
        assert client.called

    asyncio.run(run())


def test_upsert_awaits_async_client():
    async def run():
        client = DummyAsyncClient()
        proc = HarmonicProcessor(client)
        await proc.upsert([[0.1]], [{}], ["a"])
        assert client.called

    asyncio.run(run())
