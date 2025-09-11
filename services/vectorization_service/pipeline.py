"""Vectorizer pipeline placeholder."""

from typing import Any, Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Lazily initialised global vectorizer
_VECTORIZER: TfidfVectorizer | None = None


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Transform payload text into a TF-IDF embedding.

    Parameters
    ----------
    payload:
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
