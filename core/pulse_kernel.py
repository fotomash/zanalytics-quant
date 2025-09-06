try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - environment without MetaTrader5
    mt5 = None  # type: ignore

from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
import numpy as np


class PulseKernel:
    """Real-data kernel that connects directly to MetaTrader5."""

    def __init__(self) -> None:
        self.mt5_connected = False
        self.last_scores: Dict[str, Dict] = {}
        self.risk_state = {
            "trades_today": 0,
            "daily_loss": 0.0,
            "fatigue_level": 0,
            "cooling_off": False,
        }

    def connect_mt5(self) -> bool:
        """Connect to the MetaTrader5 terminal with simple retry logic."""
        if mt5 is None:  # pragma: no cover - handled in tests
            raise ImportError("MetaTrader5 package not installed")

        if not mt5.initialize():
            import time

            for i in range(3):
                time.sleep(2**i)
                if mt5.initialize():
                    break
            else:
                raise ConnectionError("MT5 connection failed")
        self.mt5_connected = True
        return True

    def process_tick(self, symbol: str) -> Dict:
        """Process a live tick for ``symbol`` and compute confluence score."""
        if mt5 is None:
            return {"error": "MetaTrader5 not available"}

        if not self.mt5_connected:
            self.connect_mt5()

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": "No tick data"}

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 200)
        if rates is None or len(rates) < 50:
            return {"error": "Insufficient bar data"}

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df.set_index("time", inplace=True)
        df.index = df.index.tz_convert("Europe/London")

        df.loc[df.index[-1], "bid"] = tick.bid
        df.loc[df.index[-1], "ask"] = tick.ask
        df.loc[df.index[-1], "last"] = getattr(tick, "last", tick.bid)
        df.loc[df.index[-1], "volume_real"] = getattr(
            tick, "volume_real", getattr(tick, "volume", 0)
        )

        score_data = self._calculate_real_confluence(df, symbol)
        self.last_scores[symbol] = score_data
        return score_data

    def _calculate_real_confluence(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Combine various analyses into a weighted confluence score."""
        smc_score = self._smc_analysis(df)
        wyckoff_score = self._wyckoff_analysis(df)
        ta_score = self._technical_analysis(df)

        weights = {"smc": 0.4, "wyckoff": 0.3, "ta": 0.3}
        total_score = (
            smc_score * weights["smc"]
            + wyckoff_score * weights["wyckoff"]
            + ta_score * weights["ta"]
        )

        if total_score >= 80:
            grade, color = "A", "green"
        elif total_score >= 60:
            grade, color = "B", "yellow"
        else:
            grade, color = "C", "red"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "score": round(total_score, 2),
            "grade": grade,
            "color": color,
            "components": {
                "smc": round(smc_score, 2),
                "wyckoff": round(wyckoff_score, 2),
                "ta": round(ta_score, 2),
            },
            "reasons": self._generate_reasons(smc_score, wyckoff_score, ta_score),
        }

    # --- Internal analysis helpers ---
    def _smc_analysis(self, df: pd.DataFrame) -> float:
        momentum = (df["close"] - df["open"]).mean()
        return float(np.clip((momentum + 1) * 50, 0, 100))

    def _wyckoff_analysis(self, df: pd.DataFrame) -> float:
        spread = (df["high"] - df["low"]).mean()
        return float(np.clip(spread * 10, 0, 100))

    def _technical_analysis(self, df: pd.DataFrame) -> float:
        rsi_series = self._rsi(df["close"])
        rsi_value = rsi_series.iloc[-1]
        return float(np.clip(100 - abs(50 - rsi_value) * 2, 0, 100))

    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        ma_up = up.ewm(alpha=1 / period, min_periods=period).mean()
        ma_down = down.ewm(alpha=1 / period, min_periods=period).mean()
        rs = ma_up / ma_down
        return 100 - (100 / (1 + rs))

    def _generate_reasons(self, smc: float, wyckoff: float, ta: float) -> List[str]:
        reasons: List[str] = []
        if smc > 70:
            reasons.append("SMC strength detected")
        if wyckoff > 70:
            reasons.append("Wyckoff pattern alignment")
        if ta > 70:
            reasons.append("Technical indicators favorable")
        if not reasons:
            reasons.append("Neutral conditions")
        return reasons
