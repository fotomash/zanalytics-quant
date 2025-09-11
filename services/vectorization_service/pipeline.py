"""Simple vectorization pipeline."""

from typing import Any, Dict

import numpy as np

from services.mcp2.vector.embeddings import embed


def process_payload(payload: Dict[str, Any]) -> np.ndarray:
    """Return an embedding for a given payload.

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
