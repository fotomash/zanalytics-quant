"""Locate fair value gaps using :class:`core.liquidity_engine.LiquidityEngine`."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.liquidity_engine import LiquidityEngine


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure ``state`` contains fair value gaps derived from ``dataframe``.

    Parameters
    ----------
    state:
        Mutable enrichment state containing a ``dataframe`` key.
    config:
        Configuration dictionary (currently unused).
    """

    df = state.get("dataframe")
    if not isinstance(df, pd.DataFrame):
        state["status"] = "FAIL"
        return state

    gaps: List[Dict[str, Any]] | None = state.get("fair_value_gaps")  # type: ignore[assignment]
    if gaps is None:
        engine = LiquidityEngine()
        gaps = engine.identify_fair_value_gaps(df)
        state["fair_value_gaps"] = gaps

    state["status"] = "PASS" if gaps else "FAIL"
    return state

