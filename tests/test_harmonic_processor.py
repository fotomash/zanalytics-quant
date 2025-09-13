import pytest

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


@pytest.mark.asyncio
async def test_upsert_uses_background_thread_for_sync_client():
    client = DummySyncClient()
    proc = HarmonicProcessor(client)
    await proc.upsert([[0.1]], [{}], [1])
    assert client.called


@pytest.mark.asyncio
async def test_upsert_awaits_async_client():
    client = DummyAsyncClient()
    proc = HarmonicProcessor(client)
    await proc.upsert([[0.1]], [{}], [1])
    assert client.called
