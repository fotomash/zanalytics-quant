"""Basic microstructure data filtering utilities."""

from __future__ import annotations

import pandas as pd


def apply_microstructure_filter(
    df: pd.DataFrame, *, max_spread: float | None = None
) -> pd.DataFrame:
    """Remove ticks that violate simple market microstructure rules.

    The filter guards against corrupt or unrealistic tick data by applying the
    following rules:

    1. ``bid`` must be strictly less than ``ask`` when both are available.
    2. Optional ``max_spread`` can cap the allowed bid/ask spread.
    3. If a volume column (``inferred_volume``/``volume``/``tickvol``) exists it
       must be positive.

    Parameters
    ----------
    df:
        Input tick dataframe.
    max_spread:
        Maximum allowed spread. Rows exceeding this threshold are dropped. If
        ``None`` the check is skipped.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe with the same columns as the input.
    """

    if df.empty:
        return df

    filtered = df.copy()

    if {"bid", "ask"}.issubset(filtered.columns):
        filtered = filtered[filtered["bid"] < filtered["ask"]]
        filtered = filtered.assign(spread=(filtered["ask"] - filtered["bid"]).abs())
        if max_spread is not None:
            filtered = filtered[filtered["spread"] <= max_spread]

    for col in ("inferred_volume", "volume", "tickvol"):
        if col in filtered.columns:
            filtered = filtered[filtered[col] > 0]
            break

    return filtered.reset_index(drop=True)
