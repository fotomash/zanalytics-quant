"""Validate structural integrity of a dataframe using :class:`SwingEngine`."""

from __future__ import annotations

from typing import Any, Dict

from core.swing_engine import SwingEngine
from enrichment.enrichment_engine import ensure_dataframe


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze ``state['dataframe']`` and update ``state`` with results.

    Parameters
    ----------
    state:
        Dictionary containing a ``dataframe`` key with a pandas ``DataFrame``.
    config:
        Configuration passed to :class:`SwingEngine`.
    """

    dataframe = ensure_dataframe(state)
    if dataframe is None:
        return state
    engine = SwingEngine(config)
    structure_breaks = engine.analyze(dataframe)
    state["structure_breaks"] = structure_breaks
    state["status"] = "FAIL" if structure_breaks else "PASS"
    return state
