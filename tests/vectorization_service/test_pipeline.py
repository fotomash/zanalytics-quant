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
    assert result.shape == (8,)


def test_process_payload_missing_text_raises(sample_payload):
    """A payload without text should raise a ValueError."""
    with pytest.raises(ValueError):
        process_payload(sample_payload)

def test_process_payload_returns_vector():
    payload = {"text": "hello"}
    result = process_payload(payload)
    assert isinstance(result, np.ndarray)
    assert result.shape == (1,)
    assert result[0] == len("hello")


def test_process_payload_validation_errors():
    with pytest.raises(ValueError):
        process_payload({"text": ""})
    with pytest.raises(ValueError):
        process_payload("not a dict")
