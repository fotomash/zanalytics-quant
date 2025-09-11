"""Context analysis extracted from :mod:`components.wyckoff_analyzer`.

The :class:`ContextAnalyzer` provides a small subset of Wyckoff analysis
focusing on the current market phase and detection of Sign of Strength/Weakness
(SOS/SOW).
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd


class ContextAnalyzer:
    """Analyze market context using simplified Wyckoff logic."""

    def analyze(self, df: pd.DataFrame) -> Dict[str, object]:
        """Return the current Wyckoff phase and SOS/SOW events."""
        return {
            "phase": self.identify_current_phase(df),
            "sos_sow": self.detect_sos_sow(df),
        }

    # --- Logic ported from components.wyckoff_analyzer -----------------------------
    def identify_current_phase(self, df: pd.DataFrame, lookback: int = 100) -> str:
        """Identify the current Wyckoff phase."""
        if len(df) < lookback:
            return "Insufficient data"

        recent_data = df.tail(lookback)
        price_range = recent_data["high"].max() - recent_data["low"].min()
        price_position = (
            (recent_data["close"].iloc[-1] - recent_data["low"].min()) / price_range
        )

        avg_volume = recent_data["volume"].mean()
        recent_volume = recent_data["volume"].tail(20).mean()
        volume_trend = recent_volume / avg_volume

        sma_20 = recent_data["close"].rolling(20).mean()
        sma_50 = (
            recent_data["close"].rolling(50).mean()
            if len(recent_data) >= 50
            else sma_20
        )

        if price_position < 0.3 and volume_trend > 1.2:
            return "Accumulation"
        if price_position > 0.7 and volume_trend > 1.2:
            return "Distribution"
        if len(sma_20) > 0 and len(sma_50) > 0:
            if sma_20.iloc[-1] > sma_50.iloc[-1] and recent_data["close"].iloc[-1] > sma_20.iloc[-1]:
                return "Markup"
            if sma_20.iloc[-1] < sma_50.iloc[-1] and recent_data["close"].iloc[-1] < sma_20.iloc[-1]:
                return "Markdown"

        return "Transitional"

    def detect_sos_sow(self, df: pd.DataFrame) -> List[Dict]:
        """Detect Sign of Strength (SOS) and Sign of Weakness (SOW)."""
        sos_sow: List[Dict] = []

        for i in range(20, len(df) - 5):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                price_change = (df["close"].iloc[i] - df["close"].iloc[i - 5]) / df["close"].iloc[i - 5]
                volume_increase = df["volume"].iloc[i] > df["volume"].iloc[i - 20 : i].mean() * 1.3
                if price_change > 0.01 and volume_increase:
                    sos_sow.append(
                        {
                            "type": "SOS",
                            "index": i,
                            "time": df.index[i],
                            "price": df["close"].iloc[i],
                            "strength": price_change * (
                                df["volume"].iloc[i] / df["volume"].iloc[i - 20 : i].mean()
                            ),
                        }
                    )
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                price_change = (df["close"].iloc[i] - df["close"].iloc[i - 5]) / df["close"].iloc[i - 5]
                volume_increase = df["volume"].iloc[i] > df["volume"].iloc[i - 20 : i].mean() * 1.3
                if price_change < -0.01 and volume_increase:
                    sos_sow.append(
                        {
                            "type": "SOW",
                            "index": i,
                            "time": df.index[i],
                            "price": df["close"].iloc[i],
                            "weakness": abs(price_change)
                            * (
                                df["volume"].iloc[i] / df["volume"].iloc[i - 20 : i].mean()
                            ),
                        }
                    )

        return sos_sow

