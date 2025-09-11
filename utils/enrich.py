"""Lightweight tick enrichment utilities.

This module provides a small helper for enriching raw tick dictionaries with
additional metadata.  The enrichment currently adds four pieces of
information:

* ``wyckoff_phase`` – placeholder phase detection (falls back to ``"Unknown"``)
* ``confidence`` – aggregated weight from a confidence matrix JSON file
* ``nudge`` – human‑readable summary combining phase and confidence
* ``embedding`` – dense vector representation of the ``nudge`` text using a
  ``SentenceTransformer`` model

The module also exposes helpers for loading the manifest and confidence matrix
files so they can be validated independently.
"""

from __future__ import annotations

from pathlib import Path
import json
import uuid
from typing import Any, Dict, List, TYPE_CHECKING

from services.mcp2.llm_config import call_local_echo
from services.mcp2 import llm_config

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from sentence_transformers import SentenceTransformer


class _MockSentenceTransformer:
    """Minimal stand‑in used when the real model is unavailable."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def encode(self, text: str) -> List[float]:  # pragma: no cover - trivial
        return [0.0] * self.dim


_MODEL: "SentenceTransformer | _MockSentenceTransformer | None" = None


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
        ``confidence``, ``nudge``, ``embedding`` and optionally ``echonudge``
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

        # Embedding vector for the nudge text
        embedding = model.encode(nudge)
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        else:  # pragma: no cover - mock model already returns list
            embedding = list(embedding)

        data.update(
            {
                "trade_id": _generate_trade_id(data.get("trade_id")),
                "wyckoff_phase": phase,
                "phase": phase,
                "confidence": confidence,
                "nudge": nudge,
                "embedding": embedding,
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


__all__ = ["enrich_ticks", "load_manifest", "load_confidence_matrix"]
