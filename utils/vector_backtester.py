import logging
import os
from typing import List, Tuple, Dict, Any

try:
    from qdrant_client import QdrantClient  # type: ignore
except Exception:  # ImportError or any other
    QdrantClient = None  # type: ignore

logger = logging.getLogger(__name__)


def score_embedding(embedding: List[float]) -> Tuple[float, float, List[Dict[str, Any]]]:
    """Score an embedding against analogs stored in Qdrant.

    Parameters
    ----------
    embedding : List[float]
        The vector representation of the tick to evaluate.

    Returns
    -------
    Tuple[float, float, List[dict]]
        Average PnL, win rate, and the payloads from the retrieved analogs.
        If Qdrant is unreachable or the client is unavailable, zeros and an
        empty list are returned.
    """

    if QdrantClient is None:
        logger.warning("Qdrant client library not available")
        return 0.0, 0.0, []

    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    collection = os.getenv("QDRANT_COLLECTION", "enriched")

    try:
        client = QdrantClient(url=url, api_key=api_key)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to initialize QdrantClient: %s", exc)
        return 0.0, 0.0, []

    try:
        results = client.search(
            collection_name=collection,
            query_vector=embedding,
            limit=10,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        logger.error("Qdrant search failed: %s", exc)
        return 0.0, 0.0, []

    payloads: List[Dict[str, Any]] = []
    pnls: List[float] = []
    wins = 0

    for point in results:
        payload = getattr(point, "payload", {}) or {}
        payloads.append(payload)
        pnl = payload.get("pnl")
        if isinstance(pnl, (int, float)):
            pnls.append(float(pnl))
        outcome = payload.get("outcome")
        if bool(outcome):
            wins += 1

    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    win_rate = wins / len(payloads) if payloads else 0.0

    return avg_pnl, win_rate, payloads
