"""Enrichment module wrapping :class:`PredictiveScorer`.

This module exposes a simple ``run`` function expected by the enrichment
service. It instantiates :class:`PredictiveScorer`, computes the maturity
score, and merges the results back into the provided ``state`` dictionary.
"""

from core.predictive_scorer import PredictiveScorer
from enrichment.enrichment_engine import run_state_module


def run(state, config):
    """Entry point for the predictive scoring enrichment module.

    Parameters
    ----------
    state : dict
        Shared enrichment state already populated by prior modules with
        intermediate analysis results (e.g. liquidity zones, Wyckoff phase,
        technical indicators).
    config : dict
        Optional configuration for :class:`PredictiveScorer`.

    The function delegates to ``PredictiveScorer.score`` which reads the
    precomputed values from ``state`` and only falls back to heavier analysis
    when necessary.
    """

    return run_state_module(state, lambda: PredictiveScorer(config), "score")
