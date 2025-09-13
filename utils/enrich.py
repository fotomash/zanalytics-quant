"""Lightweight tick enrichment utilities.

This module provides a small helper for enriching raw tick dictionaries with
additional metadata.  The enrichment currently adds four pieces of
information:

* ``wyckoff_phase`` – placeholder phase detection (falls back to ``"Unknown"``)
* ``confidence`` – aggregated weight from a confidence matrix JSON file
* ``nudge`` – human‑readable summary combining phase and confidence
* ``embedding_id`` – identifier of the vector representation stored in Qdrant

The module also exposes helpers for loading the manifest and confidence matrix
files so they can be validated independently.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import uuid
from typing import Any, Dict, List, TYPE_CHECKING

try:  # pragma: no cover - optional dependency
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - Qdrant optional
    QdrantClient = None  # type: ignore

try:
    from services.mcp2 import llm_config
    from services.mcp2.llm_config import call_local_echo
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    class _FallbackLLMConfig:
        LOCAL_THRESHOLD: float = 0.6

    llm_config = _FallbackLLMConfig()  # type: ignore

    def call_local_echo(prompt: str) -> str:  # pragma: no cover - simple echo
        return f"echo: {prompt}"


if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from sentence_transformers import SentenceTransformer


class _MockSentenceTransformer:
    """Minimal stand‑in used when the real model is unavailable."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def encode(self, text: str) -> List[float]:  # pragma: no cover - trivial
        return [0.0] * self.dim


_MODEL: "SentenceTransformer | _MockSentenceTransformer | None" = None

_QDRANT_CLIENT: "QdrantClient | None" = None


def _get_model() -> "SentenceTransformer | _MockSentenceTransformer":
    """Return a cached SentenceTransformer model instance.

    The model is loaded lazily on first use.  If the library or model weights
    are unavailable, a deterministic mock model is used instead so callers can
    continue operating with a zero vector embedding.
    """

    global _MODEL
    if _MODEL is None:
        try:  # pragma: no cover - exercised in tests via monkeypatching
            from sentence_transformers import SentenceTransformer

            _MODEL = SentenceTransformer("paraphrase-MiniLM-L3-v2")
        except Exception:  # pragma: no cover - fallback path
            _MODEL = _MockSentenceTransformer()
    return _MODEL


def load_manifest(path: str | Path) -> Dict[str, Any]:
    """Load the action manifest from ``path``.

    Parameters
    ----------
    path:
        Location of the manifest JSON file.
    """

    p = Path(path)
    if not p.exists():
        raise ValueError(f"Manifest file does not exist: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in manifest file {p}: {exc}") from exc


def load_confidence_matrix(path: str | Path) -> Dict[str, Any]:
    """Load the confidence matrix from ``path``.

    The matrix is expected to be a JSON object whose values may contain a
    ``weight`` field.  These weights will be aggregated by :func:`enrich_ticks`.
    """

    p = Path(path)
    if not p.exists():
        raise ValueError(f"Confidence matrix file does not exist: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in confidence matrix file {p}: {exc}") from exc


def _generate_trade_id(trade_id: str | None = None) -> str:
    """Return ``trade_id`` or generate a random one if missing."""

    return trade_id or uuid.uuid4().hex


def _get_qdrant_client() -> "QdrantClient | None":
    """Return a cached Qdrant client if the library is available."""

    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None and QdrantClient is not None:
        try:  # pragma: no cover - simple client creation
            url = os.environ.get("QDRANT_URL", "http://localhost:6333")
            api_key = os.environ.get("QDRANT_API_KEY")
            _QDRANT_CLIENT = QdrantClient(url=url, api_key=api_key)
        except Exception:
            _QDRANT_CLIENT = None
    return _QDRANT_CLIENT


def _store_embedding(embedding: List[float]) -> str:
    """Persist *embedding* to Qdrant and return the point ID."""

    point_id = uuid.uuid4().hex
    client = _get_qdrant_client()
    if client is None:
        return point_id
    try:  # pragma: no cover - network side effects
        from qdrant_client.http.models import PointStruct

        collection = os.environ.get("QDRANT_COLLECTION", "enriched")
        client.upsert(collection_name=collection, points=[PointStruct(id=point_id, vector=embedding)])
    except Exception:
        pass
    return point_id


def get_embedding(point_id: str) -> List[float] | None:
    """Retrieve the embedding vector for *point_id* from Qdrant."""

    client = _get_qdrant_client()
    if client is None:
        return None
    try:  # pragma: no cover - network side effects
        collection = os.environ.get("QDRANT_COLLECTION", "enriched")
        res = client.retrieve(collection_name=collection, ids=[point_id])
        if res:
            vector = getattr(res[0], "vector", None)
            if vector is not None:
                return list(vector)
    except Exception:
        return None
    return None


def enrich_ticks(
    ticks: list[dict],
    *,
    manifest_path: str | Path = "gpt-action-manifest.json",
    matrix_path: str | Path = "confidence_trace_matrix.json",
) -> list[dict]:
    """Enrich a list of tick dictionaries with analytics metadata.

    Parameters
    ----------
    ticks:
        Sequence of dictionaries representing tick/trade events. Each may already
        contain a ``trade_id`` or ``phase``/``wyckoff_phase``.
    manifest_path, matrix_path:
        Paths to the manifest and confidence matrix files respectively.

    Returns
    -------
    list[dict]
        Enriched tick dictionaries including ``trade_id``, ``phase``,
        ``confidence``, ``nudge``, ``embedding_id`` and optionally ``echonudge``
        for locally handled ticks.
    """

    # Load supporting data once
    manifest = load_manifest(manifest_path)
    matrix = load_confidence_matrix(matrix_path)

    # Aggregate confidence from matrix weights (ignoring non-dict values)
    confidence = sum(v.get("weight", 0) for v in matrix.values() if isinstance(v, dict))

    model_name = manifest.get("name_for_model", "model")
    model = _get_model()

    enriched: List[dict] = []
    whisper_queue: List[dict] = []

    for tick in ticks:
        data = dict(tick)  # shallow copy to avoid mutating caller state

        # Determine phase with backward compatibility for ``wyckoff_phase``
        phase = data.get("phase") or data.get("wyckoff_phase", "Unknown")

        # Simple nudge text combining manifest name and phase/confidence
        nudge = f"{model_name} sees {phase} phase with confidence {confidence:.2f}"

        # Embedding vector for the nudge text is stored in Qdrant
        embedding = model.encode(nudge)
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        else:  # pragma: no cover - mock model already returns list
            embedding = list(embedding)

        embedding_id = _store_embedding(embedding)

        data.update(
            {
                "trade_id": _generate_trade_id(data.get("trade_id")),
                "wyckoff_phase": phase,
                "phase": phase,
                "confidence": confidence,
                "nudge": nudge,
                "embedding_id": embedding_id,
            }
        )

        if data["confidence"] < llm_config.LOCAL_THRESHOLD or data["phase"] in {
            "spring",
            "distribution",
        }:
            data["echonudge"] = call_local_echo(
                f"Quick nudge for {data['phase']}, confidence {data['confidence']}: hold/sell/hedge?"
            )
        else:
            whisper_queue.append(data)

        enriched.append(data)

    # ``whisper_queue`` is kept for future remote processing
    return enriched


__all__ = ["enrich_ticks", "load_manifest", "load_confidence_matrix", "get_embedding"]
