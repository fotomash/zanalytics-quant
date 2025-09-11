"""Enrichment module leveraging :class:`core.wyckoff_analyzer.WyckoffAnalyzer`.

The ``run`` function executes a full Wyckoff analysis on the provided
DataFrame and merges a few key results into the shared ``state`` dictionary.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.wyckoff_analyzer import WyckoffAnalyzer


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Run Wyckoff context analysis and merge results into ``state``."""
    df: pd.DataFrame = state.get("dataframe")  # type: ignore[assignment]
    analyzer = WyckoffAnalyzer(config)
    results = analyzer.analyze(df)

    # Store selected analysis outputs under descriptive keys
    state["wyckoff_current_phase"] = results.get("current_phase")
    state["wyckoff_events"] = results.get("events")
    state["wyckoff_volume_analysis"] = results.get("volume_analysis")
    state["wyckoff_analysis"] = results

    # Update overall status based on detected phase, if any
    phase = results.get("current_phase")
    state["status"] = phase if phase else state.get("status")

    return state
