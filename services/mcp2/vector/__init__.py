"""Vector store utilities."""

try:  # pragma: no cover - optional dependency
    from .faiss_store import FaissStore
except Exception:  # pragma: no cover - faiss not installed
    FaissStore = None

__all__ = ["FaissStore"]
