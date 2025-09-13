import json
import logging
import os
import subprocess
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import talib
from scipy.signal import find_peaks

from utils.metrics import record_metrics


# ---------------------------------------------------------------------------
# Harmonic pattern detection helper
# ---------------------------------------------------------------------------

def detect_harmonic_patterns(
    df: pd.DataFrame, pivots: Dict[str, List[int]] | None = None
) -> List[Dict[str, Any]]:
    """Detect harmonic patterns using precomputed pivots when available.

    Parameters
    ----------
    df:
        Price data containing ``high`` and ``low`` columns.
    pivots:
        Optional dictionary with ``peaks`` and ``troughs`` index lists.

    Returns
    -------
    List[Dict[str, Any]]
        List of detected patterns. Each entry contains ``pattern`` name,
        ``points`` describing the pivot structure and ``completion_time`` /
        ``completion_price`` values.  If the detector is unavailable or an
        error occurs, an empty list is returned.
    """

    try:
        from utils.ncos_enhanced_analyzer import HarmonicPatternDetector

        detector = HarmonicPatternDetector()
        if pivots:
            highs = df["high"].astype(float).to_numpy()
            lows = df["low"].astype(float).to_numpy()
            pivot_points = []
            for i in pivots.get("peaks", []):
                if i < len(highs):
                    pivot_points.append(
                        {"index": int(i), "price": float(highs[i]), "type": "high"}
                    )
            for i in pivots.get("troughs", []):
                if i < len(lows):
                    pivot_points.append(
                        {"index": int(i), "price": float(lows[i]), "type": "low"}
                    )
            pivot_points.sort(key=lambda x: x["index"])
            patterns: List[Dict[str, Any]] = []
            for name, ratios in detector.patterns.items():
                patterns.extend(detector._check_pattern(pivot_points, ratios, name))
            return patterns
        return detector.detect_patterns(df)
    except Exception:  # pragma: no cover - graceful fallback
        return []


class RLAgent:
    """Placeholder reinforcement-learning agent interface."""

    def select_action(self, state: Dict[str, Any]) -> Any:  # pragma: no cover - stub
        """Return an action for ``state``."""
        return None

    def update(
        self,
        state: Dict[str, Any],
        action: Any,
        reward: float,
        next_state: Dict[str, Any],
    ) -> None:  # pragma: no cover - stub
        """Update internal policy from transition."""
        return None

    def train(self, episodes: int = 1) -> None:  # pragma: no cover - stub
        """Iteratively improve the agent over ``episodes``."""
        for _ in range(episodes):
            pass


class AdvancedProcessor:
    """Processor for advanced technical analytics.

    Currently provides vectorized Bill Williams fractal detection and
    Alligator moving-average calculations.  Results are exposed in a unified
    ``process`` method that also includes basic ATR-based volatility
    classification so downstream consumers can gate signals on volatility
    regimes.
    """

    def __init__(
        self,
        *,
        fractal_bars: int = 2,
        alligator: Dict[str, int] | None = None,
        atr_period: int = 14,
        atr_threshold: float = 0.0,
        logger: logging.Logger | None = None,
        ml_ensemble: bool = False,
        llm_max_tokens: int = 256,
        rl_agent: RLAgent | None = None,
    ) -> None:
        self.fractal_bars = fractal_bars
        self.alligator_cfg = alligator or {"jaw": 13, "teeth": 8, "lips": 5}
        self.atr_period = atr_period
        self.atr_threshold = atr_threshold
        self.logger = logger or logging.getLogger(__name__)
        self.ml_ensemble = ml_ensemble
        self.llm_max_tokens = llm_max_tokens
        self.rl_agent = rl_agent

    # ------------------------------------------------------------------
    # Fractals
    # ------------------------------------------------------------------
    @record_metrics
    def detect_fractals(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """Detect Bill Williams fractals using vectorized operations.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame containing ``high`` and ``low`` columns.

        Returns
        -------
        Dict[str, List[int]]
            Indices of upward ("up") and downward ("down") fractals.
        """

        if df.empty:
            return {"up": [], "down": []}

        highs = df["high"].astype(float).to_numpy()
        lows = df["low"].astype(float).to_numpy()
        b = int(self.fractal_bars)
        window = 2 * b + 1
        if len(df) < window:
            return {"up": [], "down": []}

        from numpy.lib.stride_tricks import sliding_window_view

        high_windows = sliding_window_view(highs, window)
        low_windows = sliding_window_view(lows, window)

        up_idx = np.where(high_windows.argmax(axis=1) == b)[0] + b
        down_idx = np.where(low_windows.argmin(axis=1) == b)[0] + b

        return {"up": up_idx.tolist(), "down": down_idx.tolist()}

    # ------------------------------------------------------------------
    # ZigZag Pivots
    # ------------------------------------------------------------------
    @record_metrics
    def detect_pivots(
        self, df: pd.DataFrame, prominence: float = 0.0
    ) -> Dict[str, List[int]]:
        """Locate swing highs and lows using SciPy ``find_peaks``.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame containing ``high`` and ``low`` columns.
        prominence: float, optional
            Minimum prominence passed to ``find_peaks``.

        Returns
        -------
        Dict[str, List[int]]
            Indices of ``peaks`` and ``troughs`` representing a basic
            ZigZag pivot series.
        """

        if df.empty:
            return {"peaks": [], "troughs": []}

        highs = df["high"].astype(float).to_numpy()
        lows = df["low"].astype(float).to_numpy()

        peak_idx, _ = find_peaks(highs, prominence=prominence)
        trough_idx, _ = find_peaks(-lows, prominence=prominence)

        return {"peaks": peak_idx.tolist(), "troughs": trough_idx.tolist()}

    # ------------------------------------------------------------------
    # Harmonic Patterns
    # ------------------------------------------------------------------
    @record_metrics
    def detect_harmonic_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify common harmonic patterns within price data.

        The method reuses :meth:`detect_pivots` to generate a sequence of
        alternating peaks and troughs.  Each group of five alternating pivots is
        evaluated against harmonic ratio templates for the Gartley, Bat,
        Butterfly, Crab and Cypher patterns using a ±5% tolerance.  Computations
        are vectorized where practical to keep processing time under 200ms for
        ~1k rows.

        Parameters
        ----------
        df: pd.DataFrame
            Data containing ``close`` prices as well as ``high`` and ``low`` for
            pivot detection.

        Returns
        -------
        List[Dict[str, Any]]
            Detected patterns with their pivot indices, potential reversal zone
            (min/max of C and D prices) and a confidence score between 0 and 1.
        """

        if df.empty:
            return []

        pivots = self.detect_pivots(df)
        points = sorted(
            [(i, 1) for i in pivots.get("peaks", [])]
            + [(i, -1) for i in pivots.get("troughs", [])]
        )
        if len(points) < 5:
            return []

        idx = np.array([p[0] for p in points], dtype=int)
        t = np.array([p[1] for p in points], dtype=int)

        from numpy.lib.stride_tricks import sliding_window_view

        type_windows = sliding_window_view(t, 5)
        alt_mask = np.all(type_windows[:, :-1] != type_windows[:, 1:], axis=1)
        if not np.any(alt_mask):
            return []

        idx_windows = sliding_window_view(idx, 5)[alt_mask]
        prices = df["close"].astype(float).to_numpy()

        tolerance = 0.05

        pattern_defs: Dict[str, Dict[str, List[float]]] = {
            "gartley": {
                "ab_xa": [0.618],
                "bc_ab": [0.382, 0.886],
                "cd_bc": [1.27, 1.618],
                "ad_xa": [0.786],
            },
            "bat": {
                "ab_xa": [0.382, 0.5],
                "bc_ab": [0.382, 0.886],
                "cd_bc": [1.618, 2.618],
                "ad_xa": [0.886],
            },
            "butterfly": {
                "ab_xa": [0.786],
                "bc_ab": [0.382, 0.886],
                "cd_bc": [1.618, 2.618],
                "ad_xa": [1.27, 1.618],
            },
            "crab": {
                "ab_xa": [0.382, 0.618],
                "bc_ab": [0.382, 0.886],
                "cd_bc": [2.618, 3.618],
                "ad_xa": [1.618],
            },
            "cypher": {
                "ab_xa": [0.382, 0.618],
                "bc_xa": [1.27, 1.414],
                "cd_bc": [0.786],
                "ad_xc": [0.786],
            },
        }

        results: List[Dict[str, Any]] = []

        for window in idx_windows:
            x, a, b, c, d = window
            xa = abs(prices[a] - prices[x])
            ab = abs(prices[b] - prices[a])
            bc = abs(prices[c] - prices[b])
            cd = abs(prices[d] - prices[c])
            ad = abs(prices[d] - prices[a])
            xc = abs(prices[c] - prices[x])

            ratios = {
                "ab_xa": ab / xa if xa else np.inf,
                "bc_ab": bc / ab if ab else np.inf,
                "cd_bc": cd / bc if bc else np.inf,
                "ad_xa": ad / xa if xa else np.inf,
                "bc_xa": bc / xa if xa else np.inf,
                "ad_xc": ad / xc if xc else np.inf,
            }

            for name, reqs in pattern_defs.items():
                errs = []
                valid = True
                for key, targets in reqs.items():
                    r = ratios.get(key, np.inf)
                    if not np.isfinite(r):
                        valid = False
                        break
                    arr = np.asarray(targets, dtype=float)
                    diff = np.abs(r - arr) / arr
                    err = float(np.min(diff))
                    if err > tolerance:
                        valid = False
                        break
                    errs.append(err)
                if valid and errs:
                    confidence = float(1.0 - np.mean(errs))
                    prz = {
                        "low": float(np.min(prices[[c, d]])),
                        "high": float(np.max(prices[[c, d]])),
                    }
                    results.append(
                        {
                            "pattern": name,
                            "points": window.tolist(),
                            "prz": prz,
                            "confidence": confidence,
                        }
                    )

        return results

    # ------------------------------------------------------------------
    # Local LLM helper
    # ------------------------------------------------------------------
    def _llm_infer(self, prompt: str) -> str:
        """Run a locally served LLM using ``LOCAL_LLM_MODEL``."""

        model = os.getenv("LOCAL_LLM_MODEL")
        if not model:
            return ""
        cmd: List[str] = ["ollama", "run", model, prompt]
        opts: Dict[str, Any] = {}
        if self.llm_max_tokens:
            opts["num_predict"] = int(self.llm_max_tokens)
        if opts:
            cmd += ["--options", json.dumps(opts)]
        try:  # pragma: no cover - external call
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return res.stdout.strip()
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("LLM inference failed: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Alligator
    # ------------------------------------------------------------------
    @record_metrics
    def calculate_alligator(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate Alligator moving averages and state classification.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame containing ``close`` prices.

        Returns
        -------
        Dict[str, List[float]]
            Jaw, Teeth, Lips arrays and classified state per bar.
        """

        if df.empty:
            return {"jaw": [], "teeth": [], "lips": [], "state": []}

        close = df["close"].astype(float).to_numpy()
        cfg = self.alligator_cfg

        jaw = talib.SMA(close, timeperiod=cfg.get("jaw", 13))
        teeth = talib.SMA(close, timeperiod=cfg.get("teeth", 8))
        lips = talib.SMA(close, timeperiod=cfg.get("lips", 5))

        state = np.where(
            (lips > teeth) & (teeth > jaw),
            "bullish",
            np.where((lips < teeth) & (teeth < jaw), "bearish", "neutral"),
        )

        return {
            "jaw": jaw.tolist(),
            "teeth": teeth.tolist(),
            "lips": lips.tolist(),
            "state": state.tolist(),
        }

    # ------------------------------------------------------------------
    # Volatility wiring (ATR)
    # ------------------------------------------------------------------
    @record_metrics
    def volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute ATR and flag bars exceeding the configured threshold."""

        if df.empty:
            return {
                "atr": [],
                "atr_threshold": self.atr_threshold,
                "atr_above_threshold": [],
            }

        high = df["high"].astype(float).to_numpy()
        low = df["low"].astype(float).to_numpy()
        close = df["close"].astype(float).to_numpy()
        atr = talib.ATR(high, low, close, timeperiod=self.atr_period)
        above = atr > self.atr_threshold
        return {
            "atr": atr.tolist(),
            "atr_threshold": self.atr_threshold,
            "atr_above_threshold": above.tolist(),
        }

    # ------------------------------------------------------------------
    # Elliott Wave heuristics
    # ------------------------------------------------------------------
    @record_metrics
    def elliott_wave(
        self,
        df: pd.DataFrame,
        pivots: Dict[str, List[int]],
        fractals: Dict[str, List[int]],
        gator: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Encode simple Elliott Wave rules with Fibonacci checks.

        Parameters
        ----------
        df: pd.DataFrame
            Price data containing ``close``.
        pivots: Dict[str, List[int]]
            Output from :meth:`detect_pivots`.
        fractals: Dict[str, List[int]]
            Output from :meth:`detect_fractals` used for validation.
        gator: Dict[str, List[float]]
            Output from :meth:`calculate_alligator` for trend confirmation.

        Returns
        -------
        Dict[str, Any]
            ``label`` describing the pattern and ``score`` between 0 and 1.
        """

        points = sorted(
            [(i, "peak") for i in pivots.get("peaks", [])]
            + [(i, "trough") for i in pivots.get("troughs", [])]
        )
        print(f"DEBUG: elliott_wave - Pivots: {pivots}")
        print(f"DEBUG: elliott_wave - Points: {points}")

        if len(points) < 5:
            return {"label": None, "score": 0.0}

        seq = points[:5]
        types = [t for _, t in seq]
        print(f"DEBUG: elliott_wave - Seq: {seq}")
        print(f"DEBUG: elliott_wave - Types: {types}")
        if any(types[i] == types[i + 1] for i in range(len(types) - 1)):
            return {"label": None, "score": 0.0}

        idx = [i for i, _ in seq]
        close = df["close"].astype(float).to_numpy()
        orientation = "bullish" if close[idx[1]] > close[idx[0]] else "bearish"
        waves = [abs(close[idx[i + 1]] - close[idx[i]]) for i in range(len(idx) - 1)]

        score = 0.5

        fib_levels = [0.382, 0.618]
        if len(waves) >= 4 and waves[0] and waves[2]:
            ratios = [waves[1] / waves[0], waves[3] / waves[2]]

            def fib_check(r: float) -> float:
                return 1.0 - min(abs(r - f) for f in fib_levels)

            score += 0.25 * max(0.0, min(1.0, sum(fib_check(r) for r in ratios) / 2))

        for i, t in seq:
            if t == "peak" and i in fractals.get("up", []):
                score += 0.05
            if t == "trough" and i in fractals.get("down", []):
                score += 0.05

        state = gator.get("state", [])
        if state:
            last_state = state[idx[-1]] if idx[-1] < len(state) else None
            if (orientation == "bullish" and last_state == "bullish") or (
                orientation == "bearish" and last_state == "bearish"
            ):
                score += 0.1

        score = float(np.clip(score, 0.0, 1.0))
        return {"label": f"impulse_{orientation}", "score": score}

    # ------------------------------------------------------------------
    # Unified process
    # ------------------------------------------------------------------
    @record_metrics
    def process(
        self,
        df: pd.DataFrame,
        *,
        fractals_only: bool = False,
        wave_only: bool = False,
    ) -> Dict[str, Any]:
        """Run advanced analytics with optional selective outputs.

        Parameters
        ----------
        df:
            Price data with ``open``, ``high``, ``low`` and ``close`` columns.
        fractals_only:
            If ``True`` return only the ``fractals`` section of the full
            analysis.  Other metrics are skipped to reduce the payload size.
        wave_only:
            If ``True`` return only the ``elliott_wave`` section.  Supporting
            analytics such as fractals and pivots are computed internally but
            omitted from the returned dictionary.  ``fractals_only`` takes
            precedence if both flags are ``True``.

        Returns
        -------
        Dict[str, Any]
            Depending on the flags, a subset of the following keys:

            ``fractals``
                Dictionary of upward and downward fractal indices.
            ``alligator``
                Moving-average lines and state classification.
            ``volatility``
                ATR series and threshold comparison.
            ``pivots``
                ZigZag swing high/low indices.
            ``harmonic_patterns``
                List of detected harmonic patterns.  Each pattern contains a
                ``pattern`` name, ``points`` describing the pivot structure,
                and ``completion_time``/``completion_price`` values.
            ``elliott_wave``
                Elliott Wave label and confidence score.
            ``ewt_forecast``
                Optional forecast string generated via LLM.
        """

        if df.empty:
            return {}
        try:
            # Fractals are needed for both modes so compute first
            fractals = self.detect_fractals(df)
            if fractals_only:
                return {"fractals": fractals}

            if wave_only:
                gator = self.calculate_alligator(df)
                pivots = self.detect_pivots(df)
                _ = detect_harmonic_patterns(df, pivots)
                elliott = self.elliott_wave(df, pivots, fractals, gator)
                return {"elliott_wave": elliott}

            gator = self.calculate_alligator(df)
            vol = self.volatility(df)
            pivots = self.detect_pivots(df)
            patterns = detect_harmonic_patterns(df, pivots)
            elliott = self.elliott_wave(df, pivots, fractals, gator)
            forecast = ""
            print(f"DEBUG: process - Elliott Label: {elliott.get('label')}")
            forecast = self._llm_infer(
                f"Provide brief forecast for {elliott['label']} with score {elliott['score']:.2f}"
            )
            return {
                "fractals": fractals,
                "alligator": gator,
                "volatility": vol,
                "pivots": pivots,
                "harmonic_patterns": patterns,
                "elliott_wave": elliott,
                "ewt_forecast": forecast,
            }
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error in advanced processing: %s", e)
            return {}


__all__ = ["AdvancedProcessor", "RLAgent"]
