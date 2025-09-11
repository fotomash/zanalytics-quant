from typing import Any, Dict, List

import pytest

from services.vectorization_service.brown_vector_store_integration import BrownVectorPipeline


class DummyResponse:
    def raise_for_status(self) -> None:
        pass


class DummySession:
    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.called: Dict[str, Any] = {}

    def post(self, url: str, json: Dict[str, Any], timeout: int) -> DummyResponse:
        self.called = {"url": url, "json": json, "timeout": timeout}
        return DummyResponse()


@pytest.fixture
def session(monkeypatch):
    dummy = DummySession()
    monkeypatch.setenv("VECTOR_DB_URL", "http://db")
    monkeypatch.setenv("VECTOR_DB_API_KEY", "key")
    monkeypatch.setattr("requests.Session", lambda: dummy)
    return dummy


def test_upsert_vector(session):
    pipeline = BrownVectorPipeline()
    pipeline.upsert_vector("id1", [1.0, 2.0], {"meta": "data"})

    assert session.called["url"] == "http://db/upsert"
    assert session.called["json"] == {
        "id": "id1",
        "embedding": [1.0, 2.0],
        "metadata": {"meta": "data"},
    }
