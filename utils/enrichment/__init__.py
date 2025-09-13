"""Enrichment utilities and processors.

This package exposes helper functions for enriching tick/bar data and
collecting higher level analytics.  It also registers lightweight analytic
processors such as the displacement/structure-shift (DSS) module.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from . import dss  # noqa: F401 - re-export for convenience

# ---------------------------------------------------------------------------
# Basic enrichment helpers (migrated from legacy ``utils.enrichment`` module)
# ---------------------------------------------------------------------------
TIMEFRAME_RULES: Dict[str, str] = {
    "M1": "1T",
    "M5": "5T",
    "M15": "15T",
    "M30": "30T",
    "H1": "1H",
    "H4": "4H",
    "D1": "1D",
    "W1": "1W",
    "MN1": "1M",
}


def aggregate_ticks_to_bars(ticks: pd.DataFrame, timeframe: str = "M1") -> pd.DataFrame:
    """Aggregate tick data into OHLC bars using pandas ``resample``.

    Parameters
    ----------
    ticks:
        Input tick data.  Must have either a ``timestamp`` column or a
        datetime index and contain ``bid`` prices.  ``ask`` prices are used to
        compute the mid price when present.
    timeframe:
        Target timeframe in MT5 notation (e.g. ``M1``, ``H1``) or any valid
        pandas offset alias.
    """
    if ticks is None or ticks.empty:
        return pd.DataFrame()

    df = ticks.copy()

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)

    rule = TIMEFRAME_RULES.get(timeframe.upper(), timeframe)

    agg: Dict[str, str | list[str]] = {"bid": ["first", "max", "min", "last"]}
    if "volume" in df.columns:
        agg["volume"] = "sum"

    resampled = df.resample(rule).agg(agg)
    resampled.columns = ["open", "high", "low", "close"] + (
        ["volume"] if "volume" in df.columns else []
    )
    resampled.dropna(subset=["open"], inplace=True)
    return resampled


def enrich_ticks(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich tick or bar data with common metrics.

    When ``bid`` and ``ask`` columns are present, mid price and spread
    statistics are derived.  Simple rolling averages and returns are computed
    on the mid price to give downstream modules immediate contextual
    information.
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    if {"bid", "ask"}.issubset(df.columns):
        df["mid_price"] = (df["bid"] + df["ask"]) / 2
        df["spread"] = df["ask"] - df["bid"]
        df["spread_bps"] = df["spread"] / df["bid"].replace(0, pd.NA) * 10000
    elif "close" in df.columns:
        df["mid_price"] = df["close"]
    elif "price" in df.columns:
        df["mid_price"] = df["price"]

    if "mid_price" in df.columns:
        df["return"] = df["mid_price"].pct_change()
        df["ma_5"] = df["mid_price"].rolling(5).mean()
        df["ma_20"] = df["mid_price"].rolling(20).mean()

    return df


__all__ = ["aggregate_ticks_to_bars", "enrich_ticks", "dss"]
