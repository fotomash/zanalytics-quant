"""Deprecated Wyckoff analyzer module.

Use :mod:`core.wyckoff_analyzer` instead.
"""

from __future__ import annotations

from warnings import warn

from core.wyckoff_analyzer import WyckoffAnalyzer

warn(
    "utils.wyckoff_analyzer is deprecated; use core.wyckoff_analyzer",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["WyckoffAnalyzer"]
