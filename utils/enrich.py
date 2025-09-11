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
from typing import Any, Dict

from sentence_transformers import SentenceTransformer

# Load a small transformer model once at import time.  The
# ``paraphrase-MiniLM-L3-v2`` model is only ~70MB and produces 384‑dimensional
# embeddings which are sufficient for unit tests and lightweight feature
# computation.
_MODEL = SentenceTransformer("paraphrase-MiniLM-L3-v2")


def load_manifest(path: str | Path) -> Dict[str, Any]:
    """Load the action manifest from ``path``.

    Parameters
    ----------
    path:
        Location of the manifest JSON file.
    """

    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_confidence_matrix(path: str | Path) -> Dict[str, Any]:
    """Load the confidence matrix from ``path``.

    The matrix is expected to be a JSON object whose values may contain a
    ``weight`` field.  These weights will be aggregated by :func:`enrich_ticks`.
    """

    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _generate_trade_id(trade_id: str | None = None) -> str:
    """Return ``trade_id`` or generate a random one if missing."""

    return trade_id or uuid.uuid4().hex


def enrich_ticks(
    tick: Dict[str, Any],
    *,
    manifest_path: str | Path = "gpt-action-manifest.json",
    matrix_path: str | Path = "confidence_trace_matrix.json",
) -> Dict[str, Any]:
    """Enrich a tick dictionary with analytics metadata.

    Parameters
    ----------
    tick:
        Dictionary representing a tick/trade event.  It may already contain a
        ``trade_id`` or ``wyckoff_phase``.
    manifest_path, matrix_path:
        Paths to the manifest and confidence matrix files respectively.

    Returns
    -------
    dict
        A new dictionary including ``trade_id``, ``wyckoff_phase``,
        ``confidence``, ``nudge`` and ``embedding`` fields.
    """

    data = dict(tick)  # shallow copy to avoid mutating caller state

    # Load supporting data
    manifest = load_manifest(manifest_path)
    matrix = load_confidence_matrix(matrix_path)

    # Wyckoff phase – placeholder: use provided value or default to "Unknown"
    phase = data.get("wyckoff_phase", "Unknown")

    # Aggregate confidence from matrix weights (ignoring non-dict values)
    confidence = sum(v.get("weight", 0) for v in matrix.values() if isinstance(v, dict))

    # Simple nudge text combining manifest name and phase/confidence
    model_name = manifest.get("name_for_model", "model")
    nudge = f"{model_name} sees {phase} phase with confidence {confidence:.2f}"

    # Embedding vector for the nudge text
    embedding = _MODEL.encode(nudge).tolist()

    data.update(
        {
            "trade_id": _generate_trade_id(data.get("trade_id")),
            "wyckoff_phase": phase,
            "confidence": confidence,
            "nudge": nudge,
            "embedding": embedding,
        }
    )

    return data


__all__ = ["enrich_ticks", "load_manifest", "load_confidence_matrix"]
