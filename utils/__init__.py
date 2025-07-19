"""Utility helpers for the Zanalytics dashboard."""

from __future__ import annotations

import pandas as pd


def enrich_ticks(df: pd.DataFrame) -> pd.DataFrame:
    """Apply lightweight enrichment to raw tick or bar data.

    Adds mid price and spread metrics which are used throughout the
    dashboard. The function expects ``bid`` and ``ask`` columns to be
    present. If they are missing the DataFrame is returned unchanged.
    """

    if {"bid", "ask"}.issubset(df.columns):
        df = df.copy()
        df["mid_price"] = (df["bid"] + df["ask"]) / 2
        df["spread"] = df["ask"] - df["bid"]
        # Avoid division by zero
        df["spread_bps"] = df["spread"] / df["bid"].replace(0, pd.NA) * 10000
    return df
