"""Detect harmonic price patterns using :class:`core.harmonic_processor.HarmonicProcessor`."""

from __future__ import annotations

from typing import Any, Dict

from core.harmonic_processor import HarmonicProcessor
from enrichment.enrichment_engine import run_data_module


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Populate ``state`` with harmonic pattern analysis."""
    return run_data_module(
        state,
        required_cols=("open", "high", "low", "close"),
        engine_factory=lambda: HarmonicProcessor(**config),
    )


__all__ = ["run"]
