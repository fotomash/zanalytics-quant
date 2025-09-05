"""Confluence scoring wrapper for existing analyzers.

This module aggregates signals from the Smart Money Concepts,
Wyckoff, and traditional technical analysis modules into a single
0-100 score.  It does not attempt to reimplement any of the
underlying logic – it simply calls the proven analyzers and
applies lightweight heuristics to map their outputs onto a common
scale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any
import numpy as np
import pandas as pd

try:
    from components.smc_analyser import SMCAnalyzer
except Exception:  # pragma: no cover - fallback when heavy deps missing
    class SMCAnalyzer:  # type: ignore
        def analyze(self, df):
            return {}

from components.wyckoff_scorer import WyckoffScorer
from components.wyckoff_agents import MultiTFResolver
from components.technical_analysis import TechnicalAnalysis


@dataclass
class ConfluenceScorer:
    """Compute a unified confluence score from multiple analyzers.

    Parameters
    ----------
    weights:
        Optional mapping of analyzer names to their contribution
        towards the final score.  The values are normalised
        automatically.
    """

    weights: Dict[str, float] | None = None
    smc: SMCAnalyzer = field(default_factory=SMCAnalyzer)
    wyckoff: WyckoffScorer = field(default_factory=WyckoffScorer)
    technical: TechnicalAnalysis = field(default_factory=TechnicalAnalysis)
    resolver: MultiTFResolver = field(default_factory=MultiTFResolver)

    def __post_init__(self) -> None:
        default = {"smc": 0.4, "wyckoff": 0.3, "technical": 0.3}
        if self.weights:
            default.update(self.weights)
        total = sum(default.values())
        self.weights = {k: v / total for k, v in default.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score(self, df: pd.DataFrame) -> Dict[str, float]:
        """Return individual and total scores.

        Parameters
        ----------
        df:
            Price data with ``open``, ``high``, ``low``, ``close`` and
            ``volume`` columns.
        """

        smc_result = self.smc.analyze(df)
        wyckoff_result = self.wyckoff.score(df) if hasattr(self.wyckoff, "score") else self.wyckoff.analyze(df)
        tech_result = self.technical.calculate_all(df)

        smc_score = self._score_smc(smc_result)
        if "wyckoff_score" in wyckoff_result:
            wyckoff_score = float(np.clip(wyckoff_result["wyckoff_score"], 0, 100))
            phase_labels = wyckoff_result.get("phase_labels")
            news_mask = wyckoff_result.get("news_mask")
        else:
            wyckoff_score = self._score_wyckoff(wyckoff_result)
            phase_labels = [wyckoff_result.get("current_phase")]
            news_mask = None
        tech_score = self._score_technical(tech_result)

        total = (
            smc_score * self.weights["smc"]
            + wyckoff_score * self.weights["wyckoff"]
            + tech_score * self.weights["technical"]
        )

        try:
            if phase_labels is not None:
                labels = np.array([phase_labels[-1]])
                conflict = self.resolver.resolve(labels, labels, labels)["conflict_mask"][-1]
            else:
                conflict = False
        except Exception:
            conflict = False
        if conflict:
            total = max(0.0, total - 10.0)
        clipped = float(np.clip(total, 0, 100))
        return {
            "smc": smc_score,
            "wyckoff": wyckoff_score,
            "technical": tech_score,
            "total": clipped,
            "score": clipped,
            "news_mask": news_mask,
        }

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------
    def _score_smc(self, res: Dict[str, Any]) -> float:
        """Very coarse heuristic based on signal counts."""
        score = 0.0
        score += len(res.get("order_blocks", [])) * 5
        score += len(res.get("fair_value_gaps", [])) * 3
        score += len(res.get("liquidity_zones", [])) * 2
        return float(np.clip(score, 0, 100))

    def _score_wyckoff(self, res: Dict[str, Any]) -> float:
        """Assign scores to Wyckoff phases and detected events."""
        phase_scores = {
            "Accumulation": 70,
            "Markup": 80,
            "Distribution": 40,
            "Markdown": 30,
        }
        score = phase_scores.get(res.get("current_phase"), 50)
        score += len(res.get("events", [])) * 2
        return float(np.clip(score, 0, 100))

    def _score_technical(self, res: Dict[str, Any]) -> float:
        """Combine a handful of technical signals."""
        score = 0.0
        try:
            if res["sma_20"].iloc[-1] > res["sma_50"].iloc[-1]:
                score += 15
            if res["ema_20"].iloc[-1] > res["ema_50"].iloc[-1]:
                score += 15
            rsi = res["rsi"].iloc[-1]
            if 40 <= rsi <= 60:
                score += 10
            macd = res["macd"].iloc[-1]
            signal = res["macd_signal"].iloc[-1]
            if macd > signal:
                score += 10
            if res["bb_middle"].iloc[-1] is not None:
                score += 10
        except Exception:
            pass
        return float(np.clip(score, 0, 100))
