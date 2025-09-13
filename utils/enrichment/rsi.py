"""Relative Strength Index (RSI) enrichment processor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class RSIProcessor:
    """Compute the Relative Strength Index for a DataFrame.

    Parameters
    ----------
    period:
        Number of periods used in the RSI calculation. Defaults to ``14`` which
        is the standard setting in many trading platforms.
    """

    period: int = 14

    def _calculate_rsi(self, series: pd.Series) -> pd.Series:
        """Return the RSI values for ``series``.

        The implementation uses a simple moving average for gains and losses to
        mirror the lightweight ``indicators.basic.rsi`` helper used elsewhere
        in the repository.  This keeps the processor dependency free while
        remaining fully deterministic.
        """

        delta = series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def enrich(
        self,
        df: pd.DataFrame,
        *,
        column: str = "close",
        return_vector: bool = False,
    ) -> Tuple[pd.DataFrame, Optional[np.ndarray]]:
        """Enrich ``df`` with an ``rsi`` column.

        Parameters
        ----------
        df:
            Input DataFrame containing at least the ``column`` specified.
        column:
            Price column on which to compute the RSI. Defaults to ``"close"``.
        return_vector:
            When ``True`` the second element of the returned tuple contains the
            raw RSI values as a :class:`numpy.ndarray`.  Otherwise ``None`` is
            returned.
        """

        if column not in df.columns:
            raise KeyError(f"DataFrame is missing required column: {column!r}")

        rsi = self._calculate_rsi(df[column])
        enriched = df.copy()
        enriched[f"rsi_{self.period}"] = rsi

        vector = rsi.to_numpy() if return_vector else None
        return enriched, vector


__all__ = ["RSIProcessor"]
