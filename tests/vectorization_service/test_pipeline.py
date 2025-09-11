import numpy as np
import pytest

from services.vectorization_service.pipeline import process_payload


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
