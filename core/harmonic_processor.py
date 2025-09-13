"""Harmonic pattern detection wrapper for enrichment pipeline."""

from __future__ import annotations

from typing import Any, Dict, List
import logging
import pandas as pd
from schemas.payloads import HarmonicResult


class HarmonicPatternDetector:
    """Lightweight harmonic pattern detector.

    This class is adapted from ``utils.ncos_enhanced_analyzer`` but strips down
    the implementation to the essentials required for the enrichment pipeline.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.patterns: Dict[str, Dict[str, float]] = {
            "GARTLEY": {"XA": 0.618, "AB": 0.382, "BC": 0.886, "CD": 0.786},
            "BUTTERFLY": {"XA": 0.786, "AB": 0.382, "BC": 0.886, "CD": 1.27},
            "BAT": {"XA": 0.382, "AB": 0.382, "BC": 0.886, "CD": 0.886},
            "CRAB": {"XA": 0.382, "AB": 0.382, "BC": 0.886, "CD": 1.618},
            "SHARK": {"XA": 0.5, "AB": 0.5, "BC": 1.618, "CD": 0.886},
            "CYPHER": {"XA": 0.382, "AB": 0.382, "BC": 1.272, "CD": 0.786},
            "THREE_DRIVES": {"XA": 0.618, "AB": 0.618, "BC": 0.618, "CD": 0.786},
            "ABCD": {"AB": 0.618, "BC": 0.618, "CD": 1.272},
        }

    # --- Detection helpers -------------------------------------------------
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect all harmonic patterns present in ``df``."""
        patterns_found: List[Dict[str, Any]] = []
        try:
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            pivots = self._find_pivots(high, low, close)
            for name, ratios in self.patterns.items():
                patterns_found.extend(self._check_pattern(pivots, ratios, name))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("error detecting harmonic patterns: %s", exc)
        return patterns_found

    def _find_pivots(self, high, low, close, window: int = 5) -> List[Dict[str, Any]]:
        pivots: List[Dict[str, Any]] = []
        for i in range(window, len(high) - window):
            if all(high[i] >= high[i - j] for j in range(1, window + 1)) and all(
                high[i] >= high[i + j] for j in range(1, window + 1)
            ):
                pivots.append({"index": i, "price": float(high[i]), "type": "high"})
            if all(low[i] <= low[i - j] for j in range(1, window + 1)) and all(
                low[i] <= low[i + j] for j in range(1, window + 1)
            ):
                pivots.append({"index": i, "price": float(low[i]), "type": "low"})
        return sorted(pivots, key=lambda x: x["index"])

    def _check_pattern(
        self, pivots: List[Dict[str, Any]], ratios: Dict[str, float], pattern_name: str
    ) -> List[Dict[str, Any]]:
        patterns: List[Dict[str, Any]] = []
        if len(pivots) < 5:
            return patterns
        for i in range(len(pivots) - 4):
            points = pivots[i : i + 5]
            if self._validate_pattern_structure(points, ratios):
                patterns.append(
                    {
                        "pattern": pattern_name,
                        "points": points,
                        "completion_time": points[-1]["index"],
                        "completion_price": points[-1]["price"],
                    }
                )
        return patterns

    def _validate_pattern_structure(
        self, points: List[Dict[str, Any]], ratios: Dict[str, float], tolerance: float = 0.05
    ) -> bool:
        try:
            xa = abs(points[1]["price"] - points[0]["price"])
            ab = abs(points[2]["price"] - points[1]["price"])
            bc = abs(points[3]["price"] - points[2]["price"])
            cd = abs(points[4]["price"] - points[3]["price"])
            for ratio_name, expected in ratios.items():
                if ratio_name == "XA":
                    actual = ab / xa if xa else 0
                elif ratio_name == "AB":
                    actual = bc / ab if ab else 0
                elif ratio_name == "BC":
                    actual = cd / bc if bc else 0
                elif ratio_name == "CD":
                    actual = cd / xa if xa else 0
                else:
                    continue
                if abs(actual - expected) > tolerance:
                    return False
            return True
        except Exception:  # pragma: no cover - defensive
            return False


class HarmonicProcessor:
    """Encapsulate harmonic pattern detection."""

    def __init__(self, detector: HarmonicPatternDetector | None = None) -> None:
        self.detector = detector or HarmonicPatternDetector()

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return harmonic pattern analysis for ``df``."""
        raw_patterns = self.detector.detect_patterns(df)
        processed: List[Dict[str, Any]] = []
        all_prices: List[float] = []
        confidences: List[float] = []
        for p in raw_patterns:
            pts = [{"index": pt["index"], "price": pt["price"]} for pt in p.get("points", [])]
            prices = [pt["price"] for pt in pts]
            if prices:
                prz = {"low": min(prices), "high": max(prices)}
                all_prices.extend(prices)
            else:
                prz = {"low": None, "high": None}
            confidence = float(len(pts)) / 5 if pts else 0.0
            processed.append(
                {
                    "pattern": p.get("pattern"),
                    "points": pts,
                    "prz": prz,
                    "confidence": confidence,
                }
            )
            confidences.append(confidence)
        aggregated_prz = {
            "low": min(all_prices) if all_prices else None,
            "high": max(all_prices) if all_prices else None,
        }
        aggregated_conf = max(confidences) if confidences else 0.0
        result = HarmonicResult(
            harmonic_patterns=processed,
            prz=aggregated_prz,
            confidence=aggregated_conf,
        )
        return {"harmonic": result}


__all__ = ["HarmonicProcessor", "HarmonicPatternDetector"]
