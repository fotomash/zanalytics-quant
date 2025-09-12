"""Deprecated SMC analyzer module.

Use :mod:`core.smc_analyzer` instead.
"""

from __future__ import annotations

from warnings import warn

from core.smc_analyzer import SMCAnalyzer

warn(
    "components.smc_analyser is deprecated; use core.smc_analyzer",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SMCAnalyzer"]
