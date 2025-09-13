"""Point of Interest vector enrichment module."""

from __future__ import annotations

from typing import Any, Dict

from enrichment.enrichment_engine import ensure_dataframe


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Identify key price/volume locations and store them as a vector.

    The vector captures the highest high, lowest low and average volume over
    the last ten rows. When ``config['upload']`` is true the vector will also
    be forwarded to the configured vector database.
    """

    df = ensure_dataframe(state, {"high", "low", "volume"})
    if df is None:
        return state

    window = int(config.get("window", 10))
    recent = df.tail(window)
    vector = [
        float(recent["high"].max()),
        float(recent["low"].min()),
        float(recent["volume"].mean()),
    ]
    state["poi_vector"] = vector

    if config.get("upload"):
        try:  # pragma: no cover - optional dependency
            from analytics.vector_db_config import add_vectors

            add_vectors([vector], [config.get("id", "poi")], [config.get("metadata", {})])
        except Exception:
            pass

    state.setdefault("status", "PASS")
    return state


__all__ = ["run"]
