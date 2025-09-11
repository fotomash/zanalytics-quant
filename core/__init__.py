"""Core package for Pulse runtime components."""

from __future__ import annotations

from .bootstrap_engine import BootstrapEngine
from .smc_analyzer import SMCAnalyzer

try:  # Optional: wyckoff analyzer may introduce circular imports
    from .wyckoff_analyzer import WyckoffAnalyzer
except Exception:  # pragma: no cover - best effort
    WyckoffAnalyzer = None  # type: ignore[assignment]

__all__ = [
    "pulse_kernel",
    "journal_sync",
    "BootstrapEngine",
    "SMCAnalyzer",
    "WyckoffAnalyzer",
]
