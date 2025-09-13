import pytest
import sys
import types

sys.modules.setdefault("talib", types.ModuleType("talib"))

# Stub heavy processor dependencies to avoid optional packages
advanced_stub = types.ModuleType("utils.processors.advanced")
advanced_stub.AdvancedProcessor = type("AdvancedProcessor", (), {})
advanced_stub.RLAgent = type("RLAgent", (), {})
sys.modules["utils.processors.advanced"] = advanced_stub

structure_stub = types.ModuleType("utils.processors.structure")
structure_stub.StructureProcessor = type("StructureProcessor", (), {})
sys.modules["utils.processors.structure"] = structure_stub

class _DummyPointStruct:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

qdrant_stub = types.ModuleType("qdrant_client")
qdrant_stub.models = types.SimpleNamespace(PointStruct=_DummyPointStruct)
sys.modules["qdrant_client"] = qdrant_stub

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


class FailingClient:
    def upsert(self, **kwargs):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_upsert_raises_value_error_on_mismatched_lengths():
    client = DummySyncClient()
    proc = HarmonicProcessor(client)
    with pytest.raises(ValueError):
        await proc.upsert([[0.1], [0.2]], [{}], [1])


@pytest.mark.asyncio
async def test_upsert_wraps_client_errors():
    client = FailingClient()
    proc = HarmonicProcessor(client)
    with pytest.raises(RuntimeError, match="Failed to upsert points to Qdrant"):
        await proc.upsert([[0.1]], [{}], [1])


@pytest.mark.asyncio
async def test_upsert_awaits_async_client():
    client = DummyAsyncClient()
    proc = HarmonicProcessor(client)
    await proc.upsert([[0.1]], [{}], [1])
    assert client.called
