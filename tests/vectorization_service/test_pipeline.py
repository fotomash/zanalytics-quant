import numpy as np
import pytest

from services.vectorization_service.pipeline import process_payload


@pytest.fixture
def payload_with_text(sample_payload):
    """Return a sample payload augmented with required text."""
    data = sample_payload.copy()
    data["text"] = "lorem ipsum"
    return data


def test_process_payload_returns_numpy_array(payload_with_text):
    """The pipeline should return a numpy array with expected shape."""
    result = process_payload(payload_with_text)
    assert isinstance(result, np.ndarray)
    assert result.shape == (384,)


def test_process_payload_missing_text_raises(sample_payload):
    """A payload without text should raise a ValueError."""
    with pytest.raises(ValueError):
        process_payload(sample_payload)


def test_process_payload_uses_embed(monkeypatch):
    payload = {"text": "hello"}

    def fake_embed(text: str):
        assert text == "hello"
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        "services.vectorization_service.pipeline.embed", fake_embed
    )
    result = process_payload(payload)
    np.testing.assert_allclose(result, np.array([0.1, 0.2, 0.3]))


def test_process_payload_validation_errors():
    with pytest.raises(ValueError):
        process_payload({"text": ""})
    with pytest.raises(ValueError):
        process_payload("not a dict")

