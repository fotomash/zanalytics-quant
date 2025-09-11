"""Validate structural integrity of a dataframe using :class:`SwingEngine`."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from core.swing_engine import SwingEngine


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze ``state['dataframe']`` and update ``state`` with results.

    Parameters
    ----------
    state:
        Dictionary containing a ``dataframe`` key with a pandas ``DataFrame``.
    config:
        Configuration passed to :class:`SwingEngine`.
    """

    engine = SwingEngine(config)
    dataframe: pd.DataFrame = state.get("dataframe")  # type: ignore[assignment]
    breaks = engine.analyze(dataframe)
    state["structure_breaks"] = breaks
    state["status"] = "FAIL" if breaks else "PASS"
    return state
