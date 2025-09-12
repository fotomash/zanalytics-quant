"""Utilities for generating embedding vectors from payload text."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Convert the payload's text field into an embedding vector.

    Parameters
    ----------
    payload:
        Mapping that must contain a non-empty ``"text"`` entry.

    Returns
    -------
    numpy.ndarray
        The embedding represented as a 1-D array of floats.

    Raises
    ------
    KeyError
        If ``payload`` lacks a ``"text"`` field.
    TypeError
        If the ``"text"`` field is not a string.
    ValueError
        If the ``"text"`` field is empty or ``payload`` is not a mapping.
    """

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary containing a 'text' key.")

    if "text" not in payload:
        raise KeyError("payload must contain a 'text' field")

    text = payload["text"]
    if not isinstance(text, str):
        raise TypeError("'text' field must be of type str")
    if not text.strip():
        raise ValueError("Payload must include a non-empty 'text' key.")

    embedding = embed(text)
    return np.asarray(embedding, dtype=float)


__all__ = ["process_payload"]

