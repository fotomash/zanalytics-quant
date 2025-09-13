"""Detect harmonic price patterns using :class:`core.harmonic_processor.HarmonicProcessor`."""

from __future__ import annotations

from typing import Any, Dict

from core.harmonic_processor import HarmonicProcessor
from enrichment.enrichment_engine import run_data_module


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Populate ``state`` with harmonic pattern analysis."""
    state = run_data_module(
        state,
        required_cols=("open", "high", "low", "close"),
        engine_factory=lambda: HarmonicProcessor(**config),
    )
    if state.get("status") != "FAIL":
        result = {
            "harmonic_patterns": state.get("harmonic_patterns", []),
            "prz": state.get("prz", []),
            "confidence": state.get("confidence", []),
        }
        state["HarmonicProcessor"] = result
    return state


__all__ = ["run"]
