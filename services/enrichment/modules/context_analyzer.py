"""Wrapper for :class:`core.context_analyzer.ContextAnalyzer`."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.context_analyzer import ContextAnalyzer


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Update ``state`` with market phase and SOS/SOW data."""
    df: pd.DataFrame = state.get("dataframe")  # type: ignore[assignment]
    analyzer = ContextAnalyzer()
    result = analyzer.analyze(df)
    state.update(result)
    return state

