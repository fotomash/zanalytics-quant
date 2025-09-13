import pytest
import fakeredis

from whisper_engine import WhisperEngine


class MockQdrantClient:
    """Simple mock of a Qdrant client that returns predefined matches."""

    def __init__(self, matches=None):
        self.matches = matches or []

    def search_similar_patterns(self, *args, **kwargs):
        return self.matches


def test_cluster_narrator_returns_dict():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    engine = WhisperEngine({})
    top_cluster = {
        "cluster_id": "top",
        "summary": "Market is bullish",
        "pattern": "trend",
        "recommendation": "Consider long positions",
    }
    result = engine.cluster_narrator(top_cluster, r, qdrant)
    assert isinstance(result, dict)
    assert set(result.keys()) >= {"narrative", "recommendation"}


def test_cluster_narrator_unknown_cluster():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    engine = WhisperEngine({})
    top_cluster = {"cluster_id": "unknown", "summary": "", "pattern": ""}
    result = engine.cluster_narrator(top_cluster, r, qdrant)
    assert result["recommendation"] == ""
    assert "No notable historical alerts" in result["narrative"]


def test_cluster_narrator_empty_memory():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    engine = WhisperEngine({})
    top_cluster = {"cluster_id": "top", "summary": "", "pattern": ""}
    result = engine.cluster_narrator(top_cluster, r, qdrant)
    assert "No notable historical alerts" in result["narrative"]
    assert result["recommendation"] == ""


def test_cluster_narrator_recommendation_format():
    r = fakeredis.FakeRedis(decode_responses=True)
    qdrant = MockQdrantClient()
    engine = WhisperEngine({})
    top_cluster = {
        "cluster_id": "top",
        "summary": "Uptrend",
        "pattern": "pattern",
        "recommendation": "Buy the breakout",
    }
    result = engine.cluster_narrator(top_cluster, r, qdrant)
    assert result["recommendation"] == result["recommendation"].strip()
