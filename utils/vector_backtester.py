"""Vector backtesting utilities using Qdrant."""

from __future__ import annotations

import logging
import os
from typing import List, Tuple, Dict, Any

try:
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - library may be missing in tests
    QdrantClient = None  # type: ignore

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "enriched")

_client: QdrantClient | None = None

if QdrantClient and QDRANT_URL:
    try:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to initialize Qdrant client: %s", exc)
        _client = None
else:
    if not QdrantClient:
        logger.warning("QdrantClient library not available; vector backtesting disabled")
    else:
        logger.warning("QDRANT_URL not set; vector backtesting disabled")


def score_embedding(embedding: List[float]) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Score an embedding against historical analogs.

    Returns a tuple of ``(average_pnl, win_rate, payloads)``. If the Qdrant
    service is unreachable or no analogs are found, zeros are returned along
    with an empty payload list.
    """

    if _client is None:
        logger.warning("Qdrant client unavailable; returning default scores")
        return 0.0, 0.0, []

    try:
        results = _client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=embedding,
            limit=10,
        )
    except Exception as exc:  # pragma: no cover - network/HTTP errors
        logger.warning("Qdrant search failed: %s", exc)
        return 0.0, 0.0, []

    payloads = [getattr(res, "payload", {}) for res in results]
    pnls = [p.get("pnl") for p in payloads if p.get("pnl") is not None]

    if not pnls:
        return 0.0, 0.0, payloads

    avg_pnl = sum(pnls) / len(pnls)
    wins = sum(1 for pnl in pnls if pnl > 0)
    win_rate = wins / len(pnls)

    return avg_pnl, win_rate, payloads
