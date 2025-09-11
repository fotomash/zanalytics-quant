"""Simple vectorization pipeline."""

from typing import Any, Dict

import numpy as np

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Return an embedding for a given payload.


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Process a single analysis payload.

    Validates the input payload and converts the ``text`` field into a dummy
    vector. The function raises :class:`ValueError` if the payload is not a
    dictionary or does not contain a non-empty ``text`` key. Exceptions are
    allowed to propagate so that they can be handled upstream.

    Returns
    -------
    numpy.ndarray
        A one-dimensional array containing the length of the provided text.

    Raises
    ------
    ValueError
        If ``payload`` is not a ``dict`` or ``text`` is missing/empty.
    """

    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary containing a 'text' key.")

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Payload must include a non-empty 'text' key.")

    # Placeholder vectorization logic: represent text by its length.
    return np.array([len(text)], dtype=float)
from sklearn.feature_extraction.text import TfidfVectorizer

# Lazily initialised global vectorizer
_VECTORIZER: TfidfVectorizer | None = None


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Transform payload text into a TF-IDF embedding.

    Parameters
    ----------
    payload:
        A mapping that **must** contain a ``text`` field. The text will be
        embedded using :func:`services.mcp2.vector.embeddings.embed`.

    Returns
    -------
    numpy.ndarray
        The embedding represented as a 1‑D numpy array.

    Raises
    ------
    ValueError
        If the payload does not include a ``text`` field.
    """

    if "text" not in payload or payload["text"] is None:
        raise ValueError("payload must contain a 'text' field")

    text = str(payload["text"])
    embedding = embed(text)
    return np.asarray(embedding, dtype=float)

        Dictionary containing a ``"text"`` field with the document to embed.

    Returns
    -------
    np.ndarray
        TF-IDF embedding of the provided text.
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
