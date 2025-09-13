"""RSI fusion vector enrichment module."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from enrichment.enrichment_engine import ensure_dataframe


def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Return a simple Relative Strength Index series."""

    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Fuse RSI statistics into a compact vector for downstream models."""

    df = ensure_dataframe(state, {"close"})
    if df is None:
        return state

    period = int(config.get("period", 14))
    rsi_series = _rsi(df["close"], period).fillna(0.0)
    last = float(rsi_series.iloc[-1]) if not rsi_series.empty else 0.0
    mean = float(rsi_series.tail(period).mean()) if not rsi_series.empty else 0.0
    vector = [last, mean]
    state["rsi_fusion_vector"] = vector

    if config.get("upload"):
        try:  # pragma: no cover - optional dependency
            from analytics.vector_db_config import add_vectors

            add_vectors([vector], [config.get("id", "rsi_fusion")], [config.get("metadata", {})])
        except Exception:
            pass

    state.setdefault("status", "PASS")
    return state


__all__ = ["run"]
