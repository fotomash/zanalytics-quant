import pytest

from utils.processors.harmonic import HarmonicVectorStore


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


@pytest.mark.asyncio
async def test_upsert_uses_background_thread_for_sync_client():
    client = DummySyncClient()
    store = HarmonicVectorStore(client)
    await store.upsert([[0.1]], [{}], [1])

    assert client.called


@pytest.mark.asyncio
async def test_upsert_awaits_async_client():
    client = DummyAsyncClient()
    store = HarmonicVectorStore(client)
    await store.upsert([[0.1]], [{}], [1])
    assert client.called
