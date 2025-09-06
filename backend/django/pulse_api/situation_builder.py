from datetime import datetime
import os
import requests
import pandas as pd
from zoneinfo import ZoneInfo

MT5_URL = os.getenv("MT5_URL", "http://mt5:5001")


def _now_ctx():
    ny = datetime.now(ZoneInfo("America/New_York"))
    session = "LONDON" if 7 <= ny.hour <= 13 else "OTHER"
    return {
        "session": session,
        "new_york_hour": ny.hour,
        "day_of_week": ny.weekday(),
    }


def _indicators_for(symbol):
    return {
        "ATR_14": {"value": None},
        "EMA_48": {"value": None},
        "EMA_200": {"value": None},
        "BB_Upper_20_2.0": {"value": None},
        "BB_Lower_20_2.0": {"value": None},
        "RSI_14": {"value": None, "is_overbought": False, "is_oversold": False},
    }


def _smc_tags(symbol):
    return {
        "break_of_structure": None,
        "change_of_character": None,
        "fair_value_gap": {},
        "recent_swing_high": None,
        "recent_swing_low": None,
        "judas_swing": None,
        "liquidity_sweep": None,
    }


def build_situation(symbol: str):
    px = {}
    if MT5_URL:
        try:
            px = requests.get(f"{MT5_URL}/symbol_info_tick/{symbol}", timeout=2).json()
        except Exception:
            px = {}
    price = px.get("last") or px.get("bid") or px.get("ask") or None

    tf_df = pd.DataFrame({"Close": [price]}) if price is not None else pd.DataFrame()

    return {
        "asset": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "time_context": _now_ctx(),
        "macro_context": {},
        "price_data": {"symbol": symbol, "Close": price} if price is not None else {},
        "indicators": _indicators_for(symbol),
        "smc_tags": _smc_tags(symbol),
        "enriched_tf_data": {"M15": tf_df, "M1": tf_df},
    }
