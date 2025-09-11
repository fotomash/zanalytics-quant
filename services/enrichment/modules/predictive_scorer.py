"""Enrichment module wrapping :class:`PredictiveScorer`.

This module exposes a simple ``run`` function expected by the enrichment
service. It instantiates :class:`PredictiveScorer`, computes the maturity
score, and merges the results back into the provided ``state`` dictionary.
"""

from core.predictive_scorer import PredictiveScorer


def run(state, config):
    """Entry point for the predictive scoring enrichment module.

    At this stage previous enrichment modules should have populated ``state``
    with data such as liquidity zones, Wyckoff phase and technical indicators.
    The :class:`PredictiveScorer` simply consumes that state and appends the
    maturity score and grade.
    """

    scorer = PredictiveScorer(config)
    result = scorer.score(state)
    state.update(result)
    return state
