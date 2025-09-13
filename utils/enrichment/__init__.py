"""Lightweight enrichment utilities and processors.

Provides helpers for aggregating tick data and computing derived features.
"""

from .core import TIMEFRAME_RULES, aggregate_ticks_to_bars, enrich_ticks
from .rsi import RSIProcessor
from .smc import process as smc_process
from . import poi

__all__ = ["aggregate_ticks_to_bars", "enrich_ticks"]
