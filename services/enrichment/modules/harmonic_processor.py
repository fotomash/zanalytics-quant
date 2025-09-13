"""Detect harmonic price patterns using :class:`core.harmonic_processor.HarmonicProcessor`."""

from __future__ import annotations

from typing import Any, Dict

from core.harmonic_processor import HarmonicProcessor
from enrichment.enrichment_engine import ensure_dataframe


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Populate ``state`` with harmonic pattern analysis."""
    df = ensure_dataframe(state, ("open", "high", "low", "close"))
    if df is None:
        return state
    engine = HarmonicProcessor(**config)
    result = engine.analyze(df)
    harmonic = result.get("harmonic")
    if harmonic is not None:
        state["harmonic"] = harmonic
    state["status"] = "PASS"

    return state


__all__ = ["run"]
