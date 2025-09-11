"""Structural break detection engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd


@dataclass
class SwingEngine:
    """Detect simple structural breaks in a numeric dataframe."""

    config: Dict[str, Any] | None = None
    threshold: float = field(init=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple assignment
        """Initialize derived configuration values."""
        self.config = self.config or {}
        self.threshold = float(self.config.get("threshold", 3.0))

    def analyze(self, dataframe: pd.DataFrame) -> List[int]:
        """Return indices where a structural break is detected.

        The first numeric column is inspected and any jump exceeding
        ``threshold`` standard deviations of its first difference is
        classified as a structural break. Non-numeric or empty dataframes
        yield no breaks.
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
        if not std or pd.isna(std):
            return []

        limit = std * self.threshold
        return diff.index[diff.abs() > limit].tolist()

