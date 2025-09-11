import asyncio
import time
from typing import Any, Dict, List, Optional

import numpy as np
import faiss


class FaissStore:
    """In-memory FAISS vector store with metadata and pruning.

    Parameters
    ----------
    dimension:
        Dimension of input embeddings.
    max_size:
        Maximum number of vectors retained in the index.
    ttl:
        Optional time-to-live in seconds for each vector. Entries older
        than ``ttl`` are removed during insertions and queries.

    The store tracks ``insertion_time`` and ``last_access`` for each
    vector. If the index exceeds ``max_size`` after TTL pruning, least
    recently used vectors are removed.
    """

    def __init__(self, dimension: int, max_size: int, ttl: Optional[float] = None):
        self.dimension = dimension
        self.max_size = max_size
        self.ttl = ttl
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._next_id = 0

    async def add(self, embedding: List[float], payload: Any) -> None:
        """Add an embedding with associated payload."""
        await asyncio.to_thread(self._add, embedding, payload)

    def _add(self, embedding: List[float], payload: Any) -> None:
        vec = np.array([embedding], dtype="float32")
        idx = self._next_id
        self._next_id += 1
        self.index.add_with_ids(vec, np.array([idx], dtype="int64"))
        now = time.time()
        self.metadata[idx] = {
            "embedding": vec[0],
            "payload": payload,
            "insertion_time": now,
            "last_access": now,
        }
        self._prune_if_needed()

    async def query(self, embedding: List[float], top_k: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Return nearest payloads for the given embedding."""
        return await asyncio.to_thread(self._query, embedding, top_k)

    def _query(self, embedding: List[float], top_k: int) -> Dict[str, List[Dict[str, Any]]]:
        self._prune_if_needed()
        if self.index.ntotal == 0:
            return {"matches": []}
        vec = np.array([embedding], dtype="float32")
        top_k = min(top_k, self.index.ntotal)
        distances, ids = self.index.search(vec, top_k)
        results: List[Dict[str, Any]] = []
        now = time.time()
        for dist, id_ in zip(distances[0], ids[0]):
            if id_ == -1:
                continue
            meta = self.metadata.get(int(id_))
            if not meta:
                continue
            meta["last_access"] = now
            results.append(
                {
                    "id": int(id_),
                    "payload": meta["payload"],
                    "distance": float(dist),
                    "insertion_time": meta["insertion_time"],
                }
            )
        return {"matches": results}

    def _prune_if_needed(self) -> None:
        if self.ttl is not None:
            self.prune_ttl(self.ttl)
        if self.index.ntotal > self.max_size:
            self.prune_lru(self.index.ntotal - self.max_size)

    def prune_ttl(self, ttl: float) -> None:
        """Remove entries older than ``ttl`` seconds."""
        now = time.time()
        to_remove = [id_ for id_, meta in self.metadata.items() if now - meta["insertion_time"] > ttl]
        if to_remove:
            self._remove_ids(to_remove)

    def prune_lru(self, num_to_remove: int) -> None:
        """Remove ``num_to_remove`` least recently used entries."""
        if num_to_remove <= 0:
            return
        sorted_ids = sorted(self.metadata.items(), key=lambda item: item[1]["last_access"])
        ids = [id_ for id_, _ in sorted_ids[:num_to_remove]]
        self._remove_ids(ids)

    def _remove_ids(self, ids: List[int]) -> None:
        for id_ in ids:
            self.metadata.pop(id_, None)
        if self.metadata:
            id_array = np.array(list(self.metadata.keys()), dtype="int64")
            vec_array = np.array([m["embedding"] for m in self.metadata.values()], dtype="float32")
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))
            self.index.add_with_ids(vec_array, id_array)
        else:
            self.index.reset()
