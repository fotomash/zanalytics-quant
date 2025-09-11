"""Utilities for producing text embeddings.

This module lazily loads a `SentenceTransformer` model on first use.  When the
dependency or model weights are unavailable, a deterministic mock model is used
to provide a stable zero vector so callers can continue operating.
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from sentence_transformers import SentenceTransformer


class _MockSentenceTransformer:
    """Fallback embedding model returning a zero vector."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def encode(self, text: str) -> List[float]:  # pragma: no cover - trivial
        return [0.0] * self.dim


_MODEL: "SentenceTransformer | _MockSentenceTransformer | None" = None


def _get_model() -> "SentenceTransformer | _MockSentenceTransformer":
    """Return a cached embedding model, initialising on first use."""

    global _MODEL
    if _MODEL is None:
        try:  # pragma: no cover - exercised via monkeypatching in tests
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:  # pragma: no cover - fallback path
            _MODEL = _MockSentenceTransformer()
    return _MODEL


def embed(text: str) -> List[float]:
    """Return an embedding vector for the given text."""

    embedding = _get_model().encode(text)
    if hasattr(embedding, "tolist"):
        return embedding.tolist()
    return list(embedding)


__all__ = ["embed"]

