from services.vectorization_service.csv_to_vector_integrated import vectorize_payload


def test_vectorize_payload_valid(sample_payload):
    embedding, metadata = vectorize_payload(sample_payload)
    assert len(embedding) == 384
    assert metadata["symbol"] == sample_payload["symbol"]
    assert metadata["volume"] == sample_payload.get("tick_volume")


def test_vectorize_payload_invalid(monkeypatch, sample_payload):
    def boom(text: str):
        raise RuntimeError("fail")
    monkeypatch.setattr(
        "services.vectorization_service.csv_to_vector_integrated.embed", boom
    )
    embedding, metadata = vectorize_payload(sample_payload)
    assert embedding == []
    assert "error" in metadata
