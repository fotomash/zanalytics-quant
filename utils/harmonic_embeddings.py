"""Embed harmonic pattern features and store them asynchronously in Qdrant.

This module previously handled Qdrant upserts directly.  It now delegates the
storage operation to :class:`utils.processors.harmonic.HarmonicVectorStore`
which provides an awaitable interface capable of working with both synchronous
and asynchronous Qdrant clients.  The public API is kept as a thin async wrapper
so existing call sites can simply ``await`` the new implementation.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Iterable, List

from qdrant_client import QdrantClient

from utils.processors.harmonic import HarmonicVectorStore

try:  # pragma: no cover - best effort fallback when deps missing
    from services.mcp2.vector.embeddings import embed
except Exception:  # pragma: no cover - deterministic zero vector fallback

    def embed(text: str) -> List[float]:  # type: ignore
        return [0.0] * 384


def _pattern_to_text(pattern: Dict[str, Any]) -> str:
    """Create a textual representation of a harmonic pattern."""
    name = pattern.get("pattern", "")
    ratios = pattern.get("ratios", {})
    ratios_str = " ".join(f"{k}:{v:.3f}" for k, v in ratios.items())
    prz = pattern.get("completion_price")
    return f"{name} ratios {ratios_str} PRZ {prz}"


async def upsert_harmonic_patterns(
    patterns: Iterable[Dict[str, Any]],
    *,
    client: QdrantClient | None = None,
    collection_name: str = "harmonic_patterns",
) -> None:
    """Embed and upsert harmonic patterns into a Qdrant collection.

    Parameters
    ----------
    patterns:
        Iterable of harmonic pattern dictionaries.
    client:
        Optional existing ``QdrantClient`` or
        ``qdrant_client.AsyncQdrantClient``.  If ``None``, a new synchronous
        client will be created using ``QDRANT_URL`` and ``QDRANT_API_KEY``
        environment variables.
    collection_name:
        Name of the Qdrant collection to upsert into.
    """

    if client is None:  # pragma: no cover - defensive creation
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key)

    store = HarmonicVectorStore(client, collection_name)

    vectors: List[List[float]] = []
    payloads: List[Dict[str, Any]] = []
    ids: List[int] = []

    for idx, pattern in enumerate(patterns):
        text = _pattern_to_text(pattern)
        vectors.append(embed(text))
        payloads.append({k: v for k, v in pattern.items() if k != "points"})
        ids.append(idx)

    if vectors:
        await store.upsert(vectors, payloads, ids)


def upsert_harmonic_patterns_sync(
    patterns: Iterable[Dict[str, Any]],
    *,
    client: QdrantClient | None = None,
    collection_name: str = "harmonic_patterns",
) -> None:
    """Synchronous wrapper around :func:`upsert_harmonic_patterns`.

    Provided for compatibility with code that expects a blocking call.
    """

    asyncio.run(
        upsert_harmonic_patterns(
            patterns, client=client, collection_name=collection_name
        )
    )


__all__ = ["upsert_harmonic_patterns", "upsert_harmonic_patterns_sync"]
