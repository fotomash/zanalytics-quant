import math

import pytest
from knowledge.LLM_intel.brown_vector_store_integration import MockVectorStore


def test_search_returns_consistent_ordering():
    store = MockVectorStore()
    vectors = [
        {"embedding": [0.0, 1.0], "metadata": {"chunk_id": "b"}},
        {"embedding": [1.0, 1.0], "metadata": {"chunk_id": "c"}},
        {"embedding": [1.0, 0.0], "metadata": {"chunk_id": "a"}},
    ]
    store.upsert(vectors)

    query = [1.0, 0.0]

    first = store.search(query, top_k=3)
    second = store.search(query, top_k=3)

    expected_ids = ["a", "c", "b"]
    assert [r["id"] for r in first] == expected_ids
    assert [r["id"] for r in second] == expected_ids
    assert first == second

    scores = [r["score"] for r in first]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(1 / math.sqrt(2))
    assert scores[2] == pytest.approx(0.0)

