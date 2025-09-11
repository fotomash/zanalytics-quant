"""Simple vectorization pipeline.


This module exposes a single :func:`process_payload` function that converts the
``"text"`` field of an input mapping into an embedding vector using the
``embed`` helper from :mod:`services.mcp2.vector.embeddings`.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Convert the payload's text into an embedding vector.

    Parameters
    ----------
    payload:
        Mapping that must contain a ``"text"`` field.

        Mapping that **must** contain a non-empty ``"text"`` field.

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
    ValueError
        If ``payload`` is not a dictionary or does not contain a valid
        ``"text"`` entry.
    """

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary containing a 'text' key.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Payload must include a non-empty 'text' key.")

    return np.asarray(embed(text), dtype=float)


__all__ = ["process_payload"]


__all__ = ["process_payload"]

