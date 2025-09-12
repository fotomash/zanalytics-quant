import numpy as np
import numpy as np
import pytest
import requests

from services.vectorization_service import pipeline
from services.vectorization_service.brown_vector_store_integration import BrownVectorPipeline


@pytest.fixture(autouse=True)
def fake_embed(monkeypatch):
    """Provide a lightweight deterministic embedding for tests."""
    monkeypatch.setattr(pipeline, "embed", lambda text: [0.1, 0.2])


def test_process_payload_generates_embedding():
    embedding = pipeline.process_payload({"text": "hello world"})
    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1 and embedding.size > 0


def test_process_payload_missing_text():
    with pytest.raises(KeyError):
        pipeline.process_payload({})


def test_process_payload_invalid_type():
    with pytest.raises(TypeError):
        pipeline.process_payload({"text": 123})


def test_upsert_vector_posts_embedding(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://example.com")
    monkeypatch.setenv("QDRANT_API_KEY", "secret")
    captured = {}

    class DummySession(requests.Session):
        def post(self, url, json, timeout):
            captured["url"] = url
            captured["json"] = json
            class Resp:
                def raise_for_status(self):
                    return None
            return Resp()

    monkeypatch.setattr(requests, "Session", DummySession)

    embedding = pipeline.process_payload({"text": "vector"})
    client = BrownVectorPipeline()
    client.upsert_vector("id1", embedding.tolist(), {"foo": "bar"})

    assert captured["url"] == "http://example.com/upsert"
    assert captured["json"] == {
        "id": "id1",
        "embedding": embedding.tolist(),
        "metadata": {"foo": "bar"},
    }


def test_brown_vector_pipeline_missing_env(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        BrownVectorPipeline()
