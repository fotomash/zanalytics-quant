"""Wrapper for :class:`core.liquidity_engine.LiquidityEngine`."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.liquidity_engine import LiquidityEngine


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Update ``state`` with liquidity, order block and FVG data."""
    df: pd.DataFrame = state.get("dataframe")  # type: ignore[assignment]
    engine = LiquidityEngine()
    result = engine.analyze(df)
    state.update(result)
    return state

