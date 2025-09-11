"""Locate fair value gaps using :class:`~core.smc_analyzer.SMCAnalyzer`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

from core.smc_analyzer import SMCAnalyzer


@dataclass
class FVGDetector:
    """Helper that delegates FVG detection to :class:`SMCAnalyzer`."""

    analyzer: SMCAnalyzer = SMCAnalyzer()

    def find(self, dataframe: pd.DataFrame) -> List[Dict[str, Any]]:
        """Return a list of fair value gaps found in ``dataframe``."""
        return self.analyzer.identify_fair_value_gaps(dataframe)


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze ``state['dataframe']`` for FVGs and update ``state``.

    Parameters
    ----------
    state:
        Mutable pipeline state containing a ``dataframe`` key.
    config:
        Configuration dictionary (currently unused).
    """

    df: pd.DataFrame | None = state.get("dataframe")  # type: ignore[assignment]
    if df is None:
        state["status"] = "FAIL"
        return state

    detector = FVGDetector()
    gaps = detector.find(df)

    state.setdefault("fair_value_gaps", []).extend(gaps)
    state["status"] = "PASS" if gaps else "FAIL"
    return state
