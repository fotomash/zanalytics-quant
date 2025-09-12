import logging
from typing import List, Dict

import numpy as np
import pandas as pd

from utils.metrics import record_metrics


class StructureProcessor:
    """Unified processor for structural market features.

    Combines detection of order blocks, fair value gaps, Wyckoff phases,
    and several forms of market manipulation.  This consolidates logic that
    previously lived across multiple analyzers into a single reusable
    component.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.wyckoff_analyzer = WyckoffAnalyzer(self.logger)

    # ------------------------------------------------------------------
    # Order Blocks & Fair Value Gaps
    # ------------------------------------------------------------------
    @record_metrics
    def identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify bullish and bearish order blocks.

        Parameters
        ----------
        df: pd.DataFrame
            DataFrame containing ``open``, ``high``, ``low`` and ``close``
            columns.
        """
        order_blocks: List[Dict] = []
        if df.empty:
            return order_blocks
        try:
            open_prices = df["open"].to_numpy()
            high = df["high"].to_numpy()
            low = df["low"].to_numpy()
            close = df["close"].to_numpy()

            bullish_idx = np.where((close > open_prices) & (np.roll(close, -1) > high))[
                0
            ]
            bearish_idx = np.where((close < open_prices) & (np.roll(close, -1) < low))[
                0
            ]

            if bullish_idx.size:
                order_blocks.extend(
                    [
                        {
                            "type": "bullish_ob",
                            "top": float(high[i]),
                            "bottom": float(open_prices[i]),
                            "index": int(i),
                            "strength": float(
                                (close[i] - open_prices[i]) / open_prices[i]
                            ),
                        }
                        for i in bullish_idx
                    ]
                )

            if bearish_idx.size:
                order_blocks.extend(
                    [
                        {
                            "type": "bearish_ob",
                            "top": float(open_prices[i]),
                            "bottom": float(low[i]),
                            "index": int(i),
                            "strength": float(
                                (open_prices[i] - close[i]) / open_prices[i]
                            ),
                        }
                        for i in bearish_idx
                    ]
                )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error identifying order blocks: %s", e)

        return order_blocks

    @record_metrics
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify bullish and bearish fair value gaps."""
        gaps: List[Dict] = []
        if df.empty:
            return gaps
        try:
            high = df["high"].to_numpy()
            low = df["low"].to_numpy()

            bullish_idx = np.where(low > np.roll(high, 2))[0]
            bearish_idx = np.where(high < np.roll(low, 2))[0]

            for i in bullish_idx:
                if i >= 2:
                    gaps.append(
                        {
                            "type": "bullish_fvg",
                            "top": float(low[i]),
                            "bottom": float(high[i - 2]),
                            "index": int(i),
                            "size": float(low[i] - high[i - 2]),
                        }
                    )

            for i in bearish_idx:
                if i >= 2:
                    gaps.append(
                        {
                            "type": "bearish_fvg",
                            "top": float(low[i - 2]),
                            "bottom": float(high[i]),
                            "index": int(i),
                            "size": float(low[i - 2] - high[i]),
                        }
                    )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error identifying fair value gaps: %s", e)

        return gaps

    # ------------------------------------------------------------------
    # Wyckoff
    # ------------------------------------------------------------------
    @record_metrics
    def analyze_wyckoff(self, df: pd.DataFrame) -> Dict:
        """Run Wyckoff phase and event analysis."""
        if df.empty:
            return {}
        return self.wyckoff_analyzer.analyze_wyckoff(df)

    # ------------------------------------------------------------------
    # Manipulation
    # ------------------------------------------------------------------
    @record_metrics
    def detect_manipulation(self, df: pd.DataFrame) -> Dict:
        """Detect various market manipulation patterns."""
        manipulation = {}
        if df.empty:
            return manipulation
        try:
            manipulation["spoofing"] = self._detect_spoofing(df)
            manipulation["layering"] = self._detect_layering(df)
            manipulation["wash_trading"] = self._detect_wash_trading(df)
            manipulation["quote_stuffing"] = self._detect_quote_stuffing(df)
            manipulation["momentum_ignition"] = self._detect_momentum_ignition(df)
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting manipulation: %s", e)
        return manipulation

    # ---- individual manipulation detectors ---------------------------
    @record_metrics
    def _detect_spoofing(self, df: pd.DataFrame) -> List[Dict]:
        events: List[Dict] = []
        if df.empty:
            return events
        try:
            if {"bid", "ask", "volume"} <= set(df.columns):
                bid = df["bid"].values
                ask = df["ask"].values
                volume = df["volume"].values
                bid_diff = np.diff(bid)
                ask_diff = np.diff(ask)
                for i in range(1, len(df)):
                    bid_change = abs(bid[i] - bid[i - 1])
                    ask_change = abs(ask[i] - ask[i - 1])
                    if (
                        bid_change > np.std(bid_diff) * 3
                        or ask_change > np.std(ask_diff) * 3
                    ) and volume[i] == 0:
                        events.append(
                            {
                                "index": int(i),
                                "timestamp": (
                                    df.index[i]
                                    if hasattr(df.index[i], "timestamp")
                                    else i
                                ),
                                "bid_change": float(bid_change),
                                "ask_change": float(ask_change),
                                "volume": float(volume[i]),
                                "severity": float(max(bid_change, ask_change)),
                            }
                        )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting spoofing: %s", e)
        return events

    @record_metrics
    def _detect_layering(self, df: pd.DataFrame) -> List[Dict]:
        events: List[Dict] = []
        if df.empty:
            return events
        try:
            if {"bid", "ask"} <= set(df.columns):
                bid = df["bid"].values
                ask = df["ask"].values
                for i in range(5, len(df)):
                    recent_bid = np.diff(bid[i - 5 : i])
                    recent_ask = np.diff(ask[i - 5 : i])
                    if np.sum(recent_bid > 0) >= 3 or np.sum(recent_ask > 0) >= 3:
                        events.append(
                            {
                                "index": int(i),
                                "pattern": "rapid_adjustments",
                                "bid_changes": recent_bid.tolist(),
                                "ask_changes": recent_ask.tolist(),
                            }
                        )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting layering: %s", e)
        return events

    @record_metrics
    def _detect_wash_trading(self, df: pd.DataFrame) -> List[Dict]:
        events: List[Dict] = []
        if df.empty:
            return events
        try:
            if {"volume", "last"} <= set(df.columns):
                volume = df["volume"].values
                last = df["last"].values
                for i in range(10, len(df)):
                    recent_volume = np.sum(volume[i - 10 : i])
                    price_range = np.max(last[i - 10 : i]) - np.min(last[i - 10 : i])
                    avg_price = np.mean(last[i - 10 : i])
                    if (
                        recent_volume > np.mean(volume) * 5
                        and price_range < avg_price * 0.001
                    ):
                        events.append(
                            {
                                "index": int(i),
                                "volume": float(recent_volume),
                                "price_range": float(price_range),
                                "suspicion_level": float(
                                    recent_volume / (price_range + 1e-10)
                                ),
                            }
                        )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting wash trading: %s", e)
        return events

    @record_metrics
    def _detect_quote_stuffing(self, df: pd.DataFrame) -> Dict:
        analysis: Dict = {}
        if df.empty:
            return analysis
        try:
            timestamps = df.index if hasattr(df, "index") else range(len(df))
            if len(timestamps) > 1:
                times = [
                    t.timestamp() if hasattr(t, "timestamp") else t for t in timestamps
                ]
                time_diffs = np.diff(times)
                rapid_quotes = np.sum(time_diffs < 0.001)
                analysis = {
                    "total_quotes": len(df),
                    "rapid_quotes": int(rapid_quotes),
                    "rapid_quote_ratio": float(rapid_quotes / len(df)),
                    "mean_time_between_quotes": float(np.mean(time_diffs)),
                    "min_time_between_quotes": float(np.min(time_diffs)),
                    "stuffing_suspected": bool(rapid_quotes > len(df) * 0.1),
                }
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting quote stuffing: %s", e)
        return analysis

    @record_metrics
    def _detect_momentum_ignition(self, df: pd.DataFrame) -> List[Dict]:
        events: List[Dict] = []
        if df.empty:
            return events
        try:
            if {"last", "volume"} <= set(df.columns):
                last = df["last"].values
                volume = df["volume"].values
                price_changes = np.diff(last) / last[:-1]
                for i in range(1, len(price_changes)):
                    if (
                        abs(price_changes[i]) > np.std(price_changes) * 3
                        and volume[i] > np.mean(volume) * 2
                    ):
                        events.append(
                            {
                                "index": int(i),
                                "price_change": float(price_changes[i]),
                                "volume": float(volume[i]),
                                "intensity": float(abs(price_changes[i]) * volume[i]),
                            }
                        )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error detecting momentum ignition: %s", e)
        return events


class WyckoffAnalyzer:
    """Micro Wyckoff analysis utilities."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.phases = ["accumulation", "markup", "distribution", "markdown"]
        self.events = [
            "PS",
            "SC",
            "AR",
            "ST",
            "BC",
            "LPS",
            "SOS",
            "LPSY",
            "UTAD",
            "LPSY2",
        ]

    @record_metrics
    def analyze_wyckoff(self, df: pd.DataFrame) -> Dict:
        results: Dict = {}
        if df.empty:
            return results
        try:
            results["phases"] = self._identify_phases(df)
            results["events"] = self._identify_events(df)
            results["volume_analysis"] = self._analyze_volume_patterns(df)
            results["effort_vs_result"] = self._analyze_effort_vs_result(df)
            results["supply_demand"] = self._analyze_supply_demand(df)
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error in Wyckoff analysis: %s", e)
        return results

    # --- phase detection -------------------------------------------------
    def _identify_phases(self, df: pd.DataFrame) -> List[Dict]:
        phases: List[Dict] = []
        if len(df) < 60 or "close" not in df.columns:
            return phases

        close = df["close"].to_numpy()
        volume = df.get("volume", pd.Series(np.ones(len(df)))).to_numpy()
        vol_20 = pd.Series(close).rolling(20).std().fillna(method="bfill").to_numpy()
        vol_50m = pd.Series(vol_20).rolling(30).mean().fillna(method="bfill").to_numpy()
        volu_20 = pd.Series(volume).rolling(20).mean().fillna(method="bfill").to_numpy()

        for i in range(50, len(df) - 10):
            try:
                if vol_20[i] < 0.75 * vol_50m[i] and volume[i] > 1.25 * volu_20[i]:
                    phases.append(
                        dict(
                            phase="accumulation",
                            start=i - 10,
                            end=i + 10,
                            strength=volume[i] / volu_20[i],
                        )
                    )
                elif (
                    vol_20[i] > 1.25 * vol_50m[i]
                    and close[i] > 1.01 * close[i - 5]
                    and volume[i] > volu_20[i]
                ):
                    phases.append(
                        dict(
                            phase="markup",
                            start=i - 5,
                            end=i + 5,
                            strength=(close[i] - close[i - 5]) / close[i - 5],
                        )
                    )
                if len(phases) > 1000:
                    self.logger.warning(
                        "Wyckoff phase detector stopped early (1000+ phases)."
                    )
                    break
            except Exception as e:  # pragma: no cover - defensive logging
                self.logger.debug("Wyckoff phase calc issue @%d: %s", i, e)
        return phases

    # --- event detection -------------------------------------------------
    def _identify_events(self, df: pd.DataFrame) -> List[Dict]:
        events: List[Dict] = []
        if df.empty:
            return events
        try:
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
            for i in range(10, len(df) - 10):
                if (
                    close[i] < close[i - 5]
                    and volume[i] > np.mean(volume[i - 10 : i])
                    and close[i + 1] > close[i]
                ):
                    events.append(
                        {
                            "event": "PS",
                            "index": int(i),
                            "price": float(close[i]),
                            "volume": float(volume[i]),
                            "description": "Preliminary Support",
                        }
                    )
            for i in range(10, len(df) - 10):
                if (
                    volume[i] > 2 * np.mean(volume[i - 10 : i])
                    and close[i] < close[i - 1]
                    and close[i + 1] > close[i]
                ):
                    events.append(
                        {
                            "event": "SC",
                            "index": int(i),
                            "price": float(close[i]),
                            "volume": float(volume[i]),
                            "description": "Selling Climax",
                        }
                    )
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error identifying Wyckoff events: %s", e)
        return events

    # --- volume analysis -------------------------------------------------
    def _analyze_volume_patterns(self, df: pd.DataFrame) -> Dict:
        analysis: Dict = {}
        if df.empty:
            return analysis
        try:
            volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
            close = df["close"].values
            volume_trend = np.polyfit(range(len(volume)), volume, 1)[0]
            price_trend = np.polyfit(range(len(close)), close, 1)[0]
            analysis = {
                "volume_trend": float(volume_trend),
                "price_trend": float(price_trend),
                "divergence": bool(
                    (price_trend > 0 and volume_trend < 0)
                    or (price_trend < 0 and volume_trend > 0)
                ),
                "avg_volume": float(np.mean(volume)),
                "volume_spikes": np.where(volume > 2 * np.mean(volume))[0].tolist(),
            }
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error analyzing volume patterns: %s", e)
        return analysis

    # --- effort vs result ------------------------------------------------
    def _analyze_effort_vs_result(self, df: pd.DataFrame) -> Dict:
        analysis: Dict = {}
        if df.empty:
            return analysis
        try:
            if {"close", "volume"} <= set(df.columns):
                close = df["close"].values
                volume = df["volume"].values
                returns = np.diff(close)
                effort = volume[1:]
                result = returns
                correlation = np.corrcoef(effort, result)[0, 1]
                analysis = {
                    "effort_result_correlation": float(correlation),
                    "avg_effort": float(np.mean(effort)),
                    "avg_result": float(np.mean(result)),
                }
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error analyzing effort vs result: %s", e)
        return analysis

    # --- supply vs demand ------------------------------------------------
    def _analyze_supply_demand(self, df: pd.DataFrame) -> Dict:
        analysis: Dict = {}
        if df.empty:
            return analysis
        try:
            if {"bid", "ask", "bid_volume", "ask_volume"} <= set(df.columns):
                bid_volume = df["bid_volume"].values
                ask_volume = df["ask_volume"].values
                total_bid = np.sum(bid_volume)
                total_ask = np.sum(ask_volume)
                analysis = {
                    "total_bid_volume": float(total_bid),
                    "total_ask_volume": float(total_ask),
                    "imbalance": float(total_bid - total_ask),
                }
        except Exception as e:  # pragma: no cover - defensive logging
            self.logger.warning("Error analyzing supply/demand: %s", e)
        return analysis
