import asyncio
import time

from services.mcp2.vector.faiss_store import FaissStore


def test_ttl_pruning(monkeypatch):
    async def run():
        store = FaissStore(dimension=8, max_size=10, ttl=1.0)
        await store.add("old_trade", [0.0] * 8, "old")
        original_time = time.time()

        # Advance time beyond TTL before inserting next item
        monkeypatch.setattr(time, "time", lambda: original_time + 2)
        await store.add("new_trade", [0.1] * 8, "new")

        result = await store.query([0.1] * 8, top_k=10)
        payloads = [m["payload"] for m in result["matches"]]
        ids = [m["id"] for m in result["matches"]]
        assert "old" not in payloads
        assert ids == ["new_trade"]

    asyncio.run(run())


def test_lru_pruning():
    async def run():
        store = FaissStore(dimension=8, max_size=1)
        await store.add("a", [0.0] * 8, "a")
        await store.add("b", [0.1] * 8, "b")

        result = await store.query([0.1] * 8, top_k=10)
        payloads = [m["payload"] for m in result["matches"]]
        ids = [m["id"] for m in result["matches"]]
        assert payloads == ["b"]
        assert ids == ["b"]

    asyncio.run(run())
