"""Helpers for scoring tick embeddings against historical vectors.

This module provides ``score_embedding`` which queries Qdrant for the
nearest analog vectors and returns simple PnL statistics.  The function is
written defensively – any network or import failures simply result in
zeroed metrics so that callers can continue operating in environments
without a running vector database.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import os

from .enrich import _get_qdrant_client


def score_embedding(
    embedding: List[float],
    limit: int = 5,
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Return analog information for *embedding*.

    Parameters
    ----------
    embedding:
        Embedding vector representing the current tick or batch.
    limit:
        Maximum number of analog vectors to consider.

    Returns
    -------
    tuple
        ``(avg_pnl, win_rate, payloads)`` where ``payloads`` is a list of
        payload dictionaries returned by Qdrant for the matched points.
    """

    client = _get_qdrant_client()
    if client is None:
        return 0.0, 0.0, []

    collection = os.environ.get("QDRANT_COLLECTION", "enriched")
    try:  # pragma: no cover - network side effects
        res = client.search(
            collection_name=collection, query_vector=embedding, limit=limit
        )
    except Exception:
        return 0.0, 0.0, []

    payloads: List[Dict[str, Any]] = []
    pnls: List[float] = []
    wins = 0
    for point in res:
        payload = getattr(point, "payload", {}) or {}
        payloads.append(payload)
        pnl = float(payload.get("pnl", 0.0))
        pnls.append(pnl)
        if pnl > 0:
            wins += 1

    if not pnls:
        return 0.0, 0.0, payloads

    avg_pnl = float(sum(pnls) / len(pnls))
    win_rate = float(wins / len(pnls))
    return avg_pnl, win_rate, payloads


__all__ = ["score_embedding"]
