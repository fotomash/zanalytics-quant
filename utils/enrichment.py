import pandas as pd
import numpy as np


def enrich_ticks(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich tick or bar data with common metrics.

    The function expects ``bid`` and ``ask`` columns where available. When
    present, it derives ``mid_price`` and ``spread`` metrics. Simple
    technical indicators like rolling averages and returns are also
    calculated on the mid price.
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
