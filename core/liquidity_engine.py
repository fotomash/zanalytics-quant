"""Liquidity analysis utilities extracted from :mod:`components.smc_analyser`.

This module exposes :class:`LiquidityEngine` which focuses on identifying
liquidity zones, order blocks and fair value gaps.  The implementation is a
light-weight subset of the original :class:`~components.smc_analyser.SMCAnalyzer`
class used across the code base.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd


class LiquidityEngine:
    """Analyze price action for liquidity, order blocks and FVGs."""

    def analyze(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """Return liquidity, order block and FVG information for ``df``.

        Parameters
        ----------
        df:
            DataFrame containing at least ``open``, ``high``, ``low`` and
            ``close`` columns.
        """

        return {
            "liquidity_zones": self.identify_liquidity_zones(df),
            "order_blocks": self.identify_order_blocks(df),
            "fair_value_gaps": self.identify_fair_value_gaps(df),
        }

    # --- Logic ported from components.smc_analyser ---------------------------------
    def identify_liquidity_zones(self, df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """Identify buy-side and sell-side liquidity zones."""
        liquidity_zones: List[Dict] = []

        rolling_high = df["high"].rolling(window=lookback).max()
        rolling_low = df["low"].rolling(window=lookback).min()

        for i in range(lookback, len(df)):
            high_count = (
                (abs(df["high"].iloc[i - lookback : i] - df["high"].iloc[i])
                 < df["high"].iloc[i] * 0.0001)
            ).sum()
            if high_count >= 2:
                liquidity_zones.append(
                    {
                        "type": "BSL",
                        "level": df["high"].iloc[i],
                        "strength": high_count / lookback,
                        "index": i,
                        "time": df.index[i],
                    }
                )

            low_count = (
                (abs(df["low"].iloc[i - lookback : i] - df["low"].iloc[i])
                 < df["low"].iloc[i] * 0.0001)
            ).sum()
            if low_count >= 2:
                liquidity_zones.append(
                    {
                        "type": "SSL",
                        "level": df["low"].iloc[i],
                        "strength": low_count / lookback,
                        "index": i,
                        "time": df.index[i],
                    }
                )

        unique_zones: List[Dict] = []
        for zone in liquidity_zones:
            is_duplicate = False
            for existing in unique_zones:
                if (
                    existing["type"] == zone["type"]
                    and abs(existing["level"] - zone["level"]) < zone["level"] * 0.001
                ):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_zones.append(zone)

        return sorted(unique_zones, key=lambda x: x["strength"], reverse=True)

    def identify_order_blocks(self, df: pd.DataFrame, min_move: float = 0.002) -> List[Dict]:
        """Identify bullish and bearish order blocks."""
        order_blocks: List[Dict] = []

        for i in range(10, len(df) - 10):
            if df["close"].iloc[i] < df["open"].iloc[i]:
                future_high = df["high"].iloc[i + 1 : i + 10].max()
                if (future_high - df["close"].iloc[i]) / df["close"].iloc[i] > min_move:
                    order_blocks.append(
                        {
                            "type": "bullish",
                            "start": df["low"].iloc[i],
                            "end": df["high"].iloc[i],
                            "index": i,
                            "time": df.index[i],
                            "strength": (future_high - df["close"].iloc[i]) / df["close"].iloc[i],
                        }
                    )
            elif df["close"].iloc[i] > df["open"].iloc[i]:
                future_low = df["low"].iloc[i + 1 : i + 10].min()
                if (df["close"].iloc[i] - future_low) / df["close"].iloc[i] > min_move:
                    order_blocks.append(
                        {
                            "type": "bearish",
                            "start": df["high"].iloc[i],
                            "end": df["low"].iloc[i],
                            "index": i,
                            "time": df.index[i],
                            "strength": (df["close"].iloc[i] - future_low) / df["close"].iloc[i],
                        }
                    )

        return sorted(order_blocks, key=lambda x: x["strength"], reverse=True)[:20]

    def identify_fair_value_gaps(self, df: pd.DataFrame, min_gap_size: float = 0.0005) -> List[Dict]:
        """Identify fair value gaps (imbalances)."""
        fvgs: List[Dict] = []

        for i in range(2, len(df)):
            gap_size = df["low"].iloc[i] - df["high"].iloc[i - 2]
            if gap_size > 0 and gap_size / df["close"].iloc[i] > min_gap_size:
                fvgs.append(
                    {
                        "type": "bullish",
                        "top": df["low"].iloc[i],
                        "bottom": df["high"].iloc[i - 2],
                        "size": gap_size,
                        "index": i,
                        "time": df.index[i],
                        "filled": False,
                    }
                )

            gap_size = df["low"].iloc[i - 2] - df["high"].iloc[i]
            if gap_size > 0 and gap_size / df["close"].iloc[i] > min_gap_size:
                fvgs.append(
                    {
                        "type": "bearish",
                        "top": df["low"].iloc[i - 2],
                        "bottom": df["high"].iloc[i],
                        "size": gap_size,
                        "index": i,
                        "time": df.index[i],
                        "filled": False,
                    }
                )

        for fvg in fvgs:
            idx = fvg["index"]
            if idx < len(df) - 1:
                future_prices = df.iloc[idx + 1 :]
                if fvg["type"] == "bullish":
                    if (future_prices["low"] <= fvg["bottom"]).any():
                        fvg["filled"] = True
                else:
                    if (future_prices["high"] >= fvg["top"]).any():
                        fvg["filled"] = True

        return fvgs

