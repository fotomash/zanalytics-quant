"""Utilities for producing text embeddings.

This module wraps the `sentence-transformers` library and exposes a single
``embed`` function.  The transformer model is loaded once at import time so
that subsequent calls do not trigger additional downloads or initialisation
overhead.
"""

from typing import List

from sentence_transformers import SentenceTransformer

# Load the model at module import so it is cached for all subsequent calls.  The
# ``all-MiniLM-L6-v2`` model provides a good balance between quality and size
# (384‑dimensional embeddings).
_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> List[float]:
    """Return an embedding vector for the given text.

    Parameters
    ----------
    text:
        The string to embed.

    Returns
    -------
    List[float]
        A dense embedding vector represented as a list of floats.
    """

    embedding = _MODEL.encode(text)
    # ``encode`` returns a numpy array; convert to a plain list for consumers.
    return embedding.tolist()
