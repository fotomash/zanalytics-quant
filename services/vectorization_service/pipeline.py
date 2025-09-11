"""Simple vectorization pipeline."""

from typing import Any, Dict

import numpy as np

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Convert the payload's text into an embedding vector.

    Parameters
    ----------
    payload:
        Mapping that must contain a ``"text"`` field.

    Returns
    -------
    numpy.ndarray
        The embedding represented as a 1‑D array of floats.

    Raises
    ------
    KeyError
        If ``payload`` lacks a ``"text"`` field.
    TypeError
        If the ``"text"`` field is not a string.
    """

    if "text" not in payload:
        raise KeyError("payload must contain a 'text' field")

    text = payload["text"]
    if not isinstance(text, str):
        raise TypeError("'text' field must be of type str")

    embedding = embed(text)
    return np.asarray(embedding, dtype=float)


__all__ = ["process_payload"]

