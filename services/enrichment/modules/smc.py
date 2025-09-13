"""Smart Money Concepts vector enrichment module."""

from __future__ import annotations

from typing import Any, Dict

from enrichment.enrichment_engine import ensure_dataframe


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a simple price/volume vector representing market structure.

    The function extracts the latest OHLCV values as a small numeric vector.
    When ``config['upload']`` is truthy the vector is also forwarded to the
    configured vector store.  This keeps the module light-weight while still
    being compatible with downstream vector databases.
    """

    df = ensure_dataframe(state, {"open", "high", "low", "close"})
    if df is None:
        return state
    last = df.iloc[-1]
    vector = [
        float(last.get("open", 0.0)),
        float(last.get("high", 0.0)),
        float(last.get("low", 0.0)),
        float(last.get("close", 0.0)),
        float(last.get("volume", 0.0)),
    ]

    if vector:
        state["smc_vector"] = vector
        if config.get("upload"):
            try:  # pragma: no cover - optional dependency
                from analytics.vector_db_config import add_vectors

                add_vectors([vector], [config.get("id", "smc")], [config.get("metadata", {})])
            except Exception:
                pass

    state.setdefault("status", "PASS")
    return state


__all__ = ["run"]
