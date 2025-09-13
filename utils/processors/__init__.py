"""Unified processor namespace.

The ``advanced`` processor depends on optional third‑party libraries such as
``talib``.  Import failures for these heavy dependencies are gracefully handled
so lighter‑weight utilities (e.g. :class:`HarmonicProcessor`) remain available
without requiring the full stack during test runs.
"""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from .advanced import AdvancedProcessor, RLAgent
except Exception:  # pragma: no cover - ignore when deps missing
    AdvancedProcessor = RLAgent = None  # type: ignore[assignment]

from .structure import StructureProcessor
from .harmonic import HarmonicProcessor

__all__ = ["AdvancedProcessor", "StructureProcessor", "RLAgent", "HarmonicProcessor"]
