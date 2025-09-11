"""Enrichment module wrapping :class:`PredictiveScorer`.

This module exposes a simple ``run`` function expected by the enrichment
service. It instantiates :class:`PredictiveScorer`, computes the maturity
score, and merges the results back into the provided ``state`` dictionary.
"""

from core.predictive_scorer import PredictiveScorer


def run(state, config):
    scorer = PredictiveScorer(config)
    result = scorer.score(state)
    state.update(result)
    return state
