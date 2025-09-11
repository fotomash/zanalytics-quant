"""Simple vectorization pipeline."""

from typing import Any, Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Lazily initialised global vectorizer
_VECTORIZER: TfidfVectorizer | None = None


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Transform payload text into a TF-IDF embedding.

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Convert the payload's text into an embedding vector.

    Parameters
    ----------
    payload:
        Dictionary containing a ``"text"`` field with the document to embed.

    Returns
    -------
    np.ndarray
        TF-IDF embedding of the provided text.

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

    global _VECTORIZER
    if _VECTORIZER is None:
        _VECTORIZER = TfidfVectorizer()
        _VECTORIZER.fit([text])

    embedding = _VECTORIZER.transform([text]).toarray()
    return np.asarray(embedding).flatten()
        Mapping that **must** contain a non-empty ``"text"`` field.

    Returns
    -------
    numpy.ndarray
        The embedding represented as a 1‑D array of floats.

    Raises
    ------
    ValueError
        If ``payload`` is not a dictionary or does not contain a valid
        ``"text"`` entry.
    """

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary containing a 'text' key.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Payload must include a non-empty 'text' key.")

    embedding = embed(text)
    return np.asarray(embedding, dtype=float)

