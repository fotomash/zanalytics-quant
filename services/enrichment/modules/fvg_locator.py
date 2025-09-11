"""Locate fair value gaps using :class:`LiquidityEngine` data."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.liquidity_engine import LiquidityEngine


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure ``state`` contains ``fair_value_gaps`` data."""
    if "fair_value_gaps" not in state:
        df: pd.DataFrame = state.get("dataframe")  # type: ignore[assignment]
        engine = LiquidityEngine()
        fvgs = engine.identify_fair_value_gaps(df)
        state["fair_value_gaps"] = fvgs
    return state

