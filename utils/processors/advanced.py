import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import talib

from utils.metrics import record_metrics


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
    ) -> None:
        self.fractal_bars = fractal_bars
        self.alligator_cfg = alligator or {"jaw": 13, "teeth": 8, "lips": 5}
        self.atr_period = atr_period
        self.atr_threshold = atr_threshold
        self.logger = logger or logging.getLogger(__name__)

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

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
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

        close = df["close"].to_numpy()
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
            return {"atr": [], "atr_threshold": self.atr_threshold, "atr_above_threshold": []}

        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr = talib.ATR(high, low, close, timeperiod=self.atr_period)
        above = atr > self.atr_threshold
        return {
            "atr": atr.tolist(),
            "atr_threshold": self.atr_threshold,
            "atr_above_threshold": above.tolist(),
        }

    # ------------------------------------------------------------------
    # Unified process
    # ------------------------------------------------------------------
    @record_metrics
    def process(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run all advanced analytics and return consolidated results."""

        if df.empty:
            return {}
        try:
            fractals = self.detect_fractals(df)
            gator = self.calculate_alligator(df)
            vol = self.volatility(df)
            return {"fractals": fractals, "alligator": gator, "volatility": vol}
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error in advanced processing: %s", e)
            return {}


__all__ = ["AdvancedProcessor"]
