"""Module running :class:`SMCAnalyzer` and updating enrichment state."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.smc_analyzer import SMCAnalyzer


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze liquidity-related structures and update ``state``.

    The function expects ``state`` to contain a ``dataframe`` key holding a
    :class:`pandas.DataFrame`.  Results from :meth:`SMCAnalyzer.analyze` are
    merged back into ``state`` and the ``status`` flag is set to ``"PASS"``
    unless critical input data is missing.
    """

    df = state.get("dataframe")
    required_cols = {"open", "high", "low", "close"}
    if not isinstance(df, pd.DataFrame) or not required_cols.issubset(df.columns):
        state["status"] = "FAIL"
        return state

    analyzer = SMCAnalyzer(config)
    results = analyzer.analyze(df)
    for key, value in results.items():
        state[key] = value

    state["status"] = "PASS"
    return state
