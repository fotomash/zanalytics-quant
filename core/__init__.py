"""Core package for Pulse runtime components."""

from __future__ import annotations

# Import only lightweight utilities to avoid pulling heavy dependencies during
# test collection.  Consumers can import additional submodules directly.
from .smc_analyzer import SMCAnalyzer

__all__ = ["SMCAnalyzer"]
