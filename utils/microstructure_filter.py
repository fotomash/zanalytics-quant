"""Utilities for filtering microstructure noise from tick data."""

from __future__ import annotations

from typing import Optional

import pandas as pd


def microstructure_filter(
    df: pd.DataFrame,
    max_spread: Optional[float] = None,
    zscore_threshold: float = 3.0,
) -> pd.DataFrame:
    """Remove ticks with abnormal spread values.

    Parameters
    ----------
    df:
        DataFrame containing at least ``bid`` and ``ask`` columns.
    max_spread:
        Absolute spread threshold. If not provided, a z-score based filter is used.
    zscore_threshold:
        Z-score threshold for dynamic spread filtering when ``max_spread`` is not
        supplied.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe with the same columns as input.
    """
    if {"bid", "ask"} - set(df.columns):
        return df

    working = df.dropna(subset=["bid", "ask"]).copy()
    working["spread"] = working["ask"] - working["bid"]

    if max_spread is None:
        spread_mean = working["spread"].mean()
        spread_std = working["spread"].std(ddof=0)
        if spread_std == 0:
            max_spread = spread_mean
        else:
            max_spread = spread_mean + zscore_threshold * spread_std

    filtered = working[working["spread"] <= max_spread].copy()
    filtered.drop(columns=["spread"], inplace=True)
    return filtered
