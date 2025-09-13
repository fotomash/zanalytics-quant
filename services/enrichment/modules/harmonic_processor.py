"""Detect harmonic price patterns using :class:`core.harmonic_processor.HarmonicProcessor`."""

from __future__ import annotations

from typing import Any, Dict

from core.harmonic_processor import HarmonicProcessor
from enrichment.enrichment_engine import run_data_module
from schemas.payloads import HarmonicResult


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Populate ``state`` with harmonic pattern analysis."""
    state = run_data_module(
        state,
        required_cols=("open", "high", "low", "close"),
        engine_factory=lambda: HarmonicProcessor(**config),
    )
    if state.get("status") != "FAIL":
        harmonic = state.get("harmonic")
        if isinstance(harmonic, HarmonicResult):
            harmonic_dict = harmonic.model_dump()
        elif isinstance(harmonic, dict):
            harmonic_dict = harmonic
        else:
            harmonic_dict = {}
        state["harmonic"] = harmonic_dict
        state["HarmonicProcessor"] = harmonic_dict
    return state


__all__ = ["run"]
