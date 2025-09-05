"""Combine multiple analysis modules into a single confluence score."""

from __future__ import annotations
from typing import Dict, Any


class ConfluenceScorer:
    """Simple weighted ensemble of different analyzers.

    Parameters
    ----------
    smc, wyckoff, technical, enhanced:
        Analyzer instances exposing a ``score`` method that returns a mapping
        with at least a ``score`` key.
    weights:
        Mapping of weightings for each component.  Missing analyzers are
        treated as neutral (score of 0).
    """

    def __init__(self, smc: Any, wyckoff: Any, technical: Any, enhanced: Any, weights: Dict[str, float]):
        self.smc = smc
        self.wyckoff = wyckoff
        self.technical = technical
        self.enhanced = enhanced
        self.weights = weights

    def score(self, data: Any) -> Dict[str, Any]:
        """Return a confluence score aggregated from all analyzers."""

        def _safe_score(analyzer: Any) -> Dict[str, Any]:
            if analyzer is None:
                return {"score": 0.0, "reasons": []}
            try:
                return analyzer.score(data)
            except Exception:
                # Fall back to neutral score if analyzer errors
                return {"score": 0.0, "reasons": []}

        smc = _safe_score(self.smc)
        wy = _safe_score(self.wyckoff)
        tech = _safe_score(self.technical)

        score_val = (
            smc.get("score", 0.0) * self.weights.get("smc", 0.0)
            + wy.get("score", 0.0) * self.weights.get("wyckoff", 0.0)
            + tech.get("score", 0.0) * self.weights.get("technical", 0.0)
        )
        grade = "Low" if score_val < 40 else "Medium" if score_val < 70 else "High"

        reasons = []
        for part in (smc, wy, tech):
            reasons.extend(part.get("reasons", []))

        return {"score": score_val, "grade": grade, "reasons": reasons}

