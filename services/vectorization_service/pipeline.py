"""Vectorizer pipeline placeholder."""

from typing import Any, Dict

import numpy as np


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
