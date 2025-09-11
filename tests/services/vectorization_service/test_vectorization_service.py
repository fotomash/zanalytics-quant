import numpy as np

from services.vectorization_service.main import VectorizationService


class DummyStore:
    def __init__(self) -> None:
        self.records: list[tuple[str, list[float], dict]] = []

    def upsert_vector(self, id: str, embedding: list[float], metadata: dict) -> None:
        self.records.append((id, embedding, metadata))


def test_process_message_flushes_batch(monkeypatch):
    store = DummyStore()
    svc = VectorizationService(batch_size=2, vector_store=store)
    monkeypatch.setattr(
        "services.vectorization_service.main.process_payload",
        lambda payload: np.array([1.0, 2.0]),
    )

    svc.process_message({"id": "a", "text": "foo"})
    assert store.records == []  # no flush yet

    svc.process_message({"id": "b", "text": "bar"})
    assert len(store.records) == 2
    assert svc.batch == []


def test_process_message_dlq_on_error():
    store = DummyStore()
    svc = VectorizationService(batch_size=1, vector_store=store)

    # Missing 'text' field should trigger DLQ entry
    svc.process_message({"id": "x"})
    assert len(svc.dlq) == 1
    assert store.records == []

