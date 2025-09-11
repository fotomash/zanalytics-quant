"""Module running :class:`~core.liquidity_engine.LiquidityEngine` and updating enrichment state."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.liquidity_engine import LiquidityEngine


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze liquidity-related structures and update ``state``.

    The function expects ``state`` to contain a ``dataframe`` key holding a
    :class:`pandas.DataFrame`.  Results from
    :meth:`LiquidityEngine.analyze` are merged back into ``state`` and the
    ``status`` flag is set to ``"PASS"`` unless critical input data is
    missing.
    """

    df = state.get("dataframe")
    required_cols = {"open", "high", "low", "close"}
    if not isinstance(df, pd.DataFrame) or not required_cols.issubset(df.columns):
        state["status"] = "FAIL"
        return state

    engine = LiquidityEngine()
    results = engine.analyze(df)
    state.update(results)

    state["status"] = "PASS"
    return state
