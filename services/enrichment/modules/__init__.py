"""Enrichment service modules."""
"""Enrichment service modules.

This package exposes individual enrichment stages used by the enrichment
pipeline.  Aliases are registered for modules whose canonical names differ from
their file names.
Provides convenient aliases so modules can be loaded by simplified names in
:mod:`services.enrichment.pipeline`.
"""

from __future__ import annotations

import sys

from . import context_analyzer as context
from . import fvg_locator as fvg
from . import liquidity_engine as liquidity
from . import predictive_scorer
from . import structure_validator

# Register shorthand aliases so callers can refer to modules by logical name.
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
