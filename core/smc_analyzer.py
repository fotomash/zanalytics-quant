"""Shim module exposing :class:`SMCAnalyzer` from :mod:`utils.smc_analyzer`.

The original implementation lives in ``utils``.  This module re-exports the
class under the ``core`` namespace so that consumers can depend on a stable
import path.
"""

from __future__ import annotations

from utils.smc_analyzer import SMCAnalyzer as _SMCAnalyzer


class SMCAnalyzer(_SMCAnalyzer):
    """Thin wrapper around :class:`utils.smc_analyzer.SMCAnalyzer`.

    Parameters
    ----------
    config:
        Optional configuration dictionary retained for interface
        compatibility.  The base implementation does not currently make use
        of this but callers may supply settings for future extensions.
    """

    def __init__(self, config: dict | None = None):
        super().__init__()
        self.config = config or {}


__all__ = ["SMCAnalyzer"]
