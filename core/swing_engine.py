"""Structural break detection engine."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


class SwingEngine:
    """Detect simple structural breaks in a numeric dataframe.

    Parameters
    ----------
    config:
        Optional configuration dictionary. Currently supports a
        ``threshold`` key controlling how many standard deviations a
        change must exceed to count as a break. Defaults to ``3.0``.
    """

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.threshold = float(self.config.get("threshold", 3.0))

    def analyze(self, dataframe: pd.DataFrame) -> List[int]:
        """Return indices where a structural break is detected.

        The method examines the first numeric column and flags points where
        the absolute change from the previous value exceeds ``threshold``
        times the standard deviation of all first differences. Empty or
        non-numeric dataframes yield no breaks.
        """

        if dataframe is None or dataframe.empty:
            return []

        numeric_df = dataframe.select_dtypes(include="number")
        if numeric_df.empty:
            return []

        series = numeric_df.iloc[:, 0]
        diff = series.diff().dropna()
        if diff.empty:
            return []

        std = diff.std()
        if std == 0 or pd.isna(std):
            return []

        threshold = std * self.threshold
        indices = diff.index[diff.abs() > threshold].tolist()
        return indices
