import asyncio
import time

from services.mcp2.vector.faiss_store import FaissStore


def test_ttl_pruning(monkeypatch):
    async def run():
        store = FaissStore(dimension=8, max_size=10, ttl=1.0)
        await store.add([0.0] * 8, "old")
        original_time = time.time()

        # Advance time beyond TTL before inserting next item
        monkeypatch.setattr(time, "time", lambda: original_time + 2)
        await store.add([0.1] * 8, "new")

        result = await store.query([0.1] * 8, top_k=10)
        payloads = [m["payload"] for m in result["matches"]]
        assert "old" not in payloads

    asyncio.run(run())


def test_lru_pruning():
    async def run():
        store = FaissStore(dimension=8, max_size=1)
        await store.add([0.0] * 8, "a")
        await store.add([0.1] * 8, "b")

        result = await store.query([0.1] * 8, top_k=10)
        payloads = [m["payload"] for m in result["matches"]]
        assert payloads == ["b"]

    asyncio.run(run())
