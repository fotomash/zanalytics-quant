"""Enrichment module wrapping :class:`core.context_analyzer.ContextAnalyzer`.

This module exposes a ``run`` function compatible with the enrichment pipeline
that analyzes market context and records Wyckoff-inspired phase information and
SOS/SOW events in the shared ``state`` dictionary.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.context_analyzer import ContextAnalyzer


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Run context analysis and merge results into ``state``.

    Parameters
    ----------
    state:
        Mutable pipeline state expected to contain a ``dataframe`` key.
    config:
        Configuration dictionary (currently unused).
    """

    df = state.get("dataframe")
    required_cols = {"open", "high", "low", "close", "volume"}
    if not isinstance(df, pd.DataFrame) or not required_cols.issubset(df.columns):
        state["status"] = "FAIL"
        return state

    analyzer = ContextAnalyzer()
    results = analyzer.analyze(df)

    state.update(results)
    state["status"] = "PASS"
    return state

