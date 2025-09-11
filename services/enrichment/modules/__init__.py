"""Enrichment service modules."""

from __future__ import annotations

import sys

from . import context_analyzer as context
from . import fvg_locator as fvg
from . import liquidity_engine as liquidity
from . import predictive_scorer
from . import structure_validator

# Register aliases so ``import_module`` can load them by name.
sys.modules[__name__ + ".context"] = context
sys.modules[__name__ + ".fvg"] = fvg
sys.modules[__name__ + ".liquidity"] = liquidity

__all__ = [
    "context",
    "fvg",
    "liquidity",
    "predictive_scorer",
    "structure_validator",
]

