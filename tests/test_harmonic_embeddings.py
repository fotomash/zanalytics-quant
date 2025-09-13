"""Tests for harmonic pattern embedding and upsert."""

import pytest
from qdrant_client import QdrantClient, models

from utils.harmonic_embeddings import upsert_harmonic_patterns


@pytest.mark.asyncio
async def test_upsert_harmonic_patterns() -> None:
    client = QdrantClient(location=":memory:")
    client.recreate_collection(
        collection_name="harmonic_patterns",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )
    patterns = [
        {
            "pattern": "GARTLEY",
            "ratios": {"XA": 0.618, "AB": 0.382},
            "completion_price": 1.23,
        }
    ]
    await upsert_harmonic_patterns(patterns, client=client)
    points, _ = client.scroll(
        collection_name="harmonic_patterns", limit=10, with_vectors=True
    )
    assert len(points) == 1
    assert points[0].payload["pattern"] == "GARTLEY"
    assert len(points[0].vector) == 384
