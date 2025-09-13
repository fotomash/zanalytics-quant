"""Embed and store harmonic pattern features in Qdrant."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Iterable, List

from qdrant_client import QdrantClient, models

from services.mcp2.vector.embeddings import embed


def _pattern_to_text(pattern: Dict[str, Any]) -> str:
    """Create a textual representation of a harmonic pattern."""
    name = pattern.get("pattern", "")
    ratios = pattern.get("ratios", {})
    ratios_str = " ".join(f"{k}:{v:.3f}" for k, v in ratios.items())
    prz = pattern.get("completion_price")
    return f"{name} ratios {ratios_str} PRZ {prz}"


def upsert_harmonic_patterns(
    patterns: Iterable[Dict[str, Any]],
    *,
    client: QdrantClient | None = None,
    collection_name: str = "harmonic_patterns",
    batch_size: int = 1000,
) -> None:
    """Embed and upsert harmonic patterns into a Qdrant collection.

    Parameters
    ----------
    patterns:
        Iterable of harmonic pattern dictionaries.
    client:
        Optional existing ``QdrantClient``. If ``None``, a new client will be
        created using ``QDRANT_URL`` and ``QDRANT_API_KEY`` environment variables.
    collection_name:
        Name of the Qdrant collection to upsert into.
    batch_size:
        Number of points to upsert in a single batch.
    """

    if client is None:
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key)

    points: List[models.PointStruct] = []
    for idx, pattern in enumerate(patterns, 1):
        text = _pattern_to_text(pattern)
        vector = embed(text)
        payload = {k: v for k, v in pattern.items() if k != "points"}
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=payload,
            )
        )
        if idx % batch_size == 0:
            client.upsert(collection_name=collection_name, points=points)
            points = []
    if points:
        client.upsert(collection_name=collection_name, points=points)


__all__ = ["upsert_harmonic_patterns"]
