"""Price/volume divergence vector enrichment module."""

from __future__ import annotations

from typing import Any, Dict

from enrichment.enrichment_engine import ensure_dataframe


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a simple divergence vector between price and volume changes.

    The vector contains the last five differences between percentage changes
    in closing price and volume. This representation can be stored in a
    vector database when ``config['upload']`` is enabled.
    """

    df = ensure_dataframe(state, {"close", "volume"})
    if df is None or len(df) < 2:
        return state

    pct_price = df["close"].pct_change()
    pct_vol = df["volume"].pct_change()
    divergence = (pct_price - pct_vol).fillna(0.0)
    vector = divergence.tail(5).astype(float).tolist()

    if vector:
        state["divergence_vector"] = vector
        if config.get("upload"):
            try:  # pragma: no cover - optional dependency
                from analytics.vector_db_config import add_vectors

                add_vectors(
                    [vector],
                    [config.get("id", "divergence")],
                    [config.get("metadata", {})],
                )
            except Exception:
                pass

    state.setdefault("status", "PASS")
    return state


__all__ = ["run"]
