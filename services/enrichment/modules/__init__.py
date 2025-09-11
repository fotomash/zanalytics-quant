"""Enrichment service modules.

Aliases are provided for modules whose filenames differ from their import
names in :mod:`services.enrichment.pipeline`.
"""

from __future__ import annotations

import sys

from . import context_analyzer as context
from . import liquidity_engine as liquidity
from . import fvg_locator as fvg
from . import predictive_scorer
from . import structure_validator

# Register aliases so ``import_module`` can load them by name.
sys.modules[__name__ + ".context"] = context
sys.modules[__name__ + ".liquidity"] = liquidity
sys.modules[__name__ + ".fvg"] = fvg

__all__ = [
    "context",
    "liquidity",
    "fvg",
    "predictive_scorer",
    "structure_validator",
]
"""Enrichment service modules."""

from . import context_analyzer, fvg_locator, liquidity_engine, predictive_scorer, structure_validator

__all__ = [
    "context_analyzer",
    "fvg_locator",
    "liquidity_engine",
    "predictive_scorer",
    "structure_validator",
]
from . import liquidity_engine

__all__ = ["liquidity_engine"]
