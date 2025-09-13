import pytest
import fakeredis
from unittest.mock import MagicMock

# Import the cluster_narrator function, skipping tests if not available.
cluster_module = pytest.importorskip("cluster_narrator")
cluster_narrator = cluster_module.cluster_narrator


class MockQdrantClient:
    """Simple mock of a Qdrant client that returns predefined payloads."""

    def __init__(self, payloads=None):
        self.payloads = payloads or {}

    def search(self, *args, **kwargs):
        # For testing we assume the query vector contains the cluster key directly.
        query_vector = kwargs.get("query_vector") or args[1] if len(args) > 1 else None
        if query_vector in self.payloads:
            return [MagicMock(payload=self.payloads[query_vector])]
        return []


def test_cluster_narrator_returns_dict():
    r = fakeredis.FakeRedis(decode_responses=True)
    r.hset("cluster:top", mapping={"narrative": "Market is bullish", "recommendation": "Consider long positions"})
    qdrant = MockQdrantClient({"top": {"narrative": "Market is bullish", "recommendation": "Consider long positions"}})
    result = cluster_narrator("top", r, qdrant)
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"narrative", "recommendation"}


def test_cluster_narrator_unknown_cluster():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    result = cluster_narrator("unknown", r, qdrant)
    assert not result["narrative"]
    assert not result["recommendation"]


def test_cluster_narrator_empty_memory():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    result = cluster_narrator("top", r, qdrant)
    assert not result["narrative"]
    assert not result["recommendation"]


def test_cluster_narrator_recommendation_format():
    r = fakeredis.FakeRedis(decode_responses=True)
    r.hset("cluster:top", mapping={"narrative": "Uptrend", "recommendation": "Buy the breakout"})
    qdrant = MockQdrantClient({"top": {"narrative": "Uptrend", "recommendation": "Buy the breakout"}})
    result = cluster_narrator("top", r, qdrant)
    assert result["recommendation"] == result["recommendation"].strip()
