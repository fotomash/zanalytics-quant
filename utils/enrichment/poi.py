"""Point‑of‑interest (POI) feature processor.

The :func:`run` function extracts simple support/resistance style
features from price data and returns both a dictionary of values and a
vector representation suitable for downstream models.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


def _to_dataframe(data: Any) -> pd.DataFrame:
    """Best‑effort conversion of *data* to ``pd.DataFrame``.

    The processor accepts either an existing ``DataFrame`` or any mapping/
    iterable that can be passed to ``pd.DataFrame``.
    """
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data
    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def run(data: Any) -> Tuple[Dict[str, float], List[float]]:
    """Return basic point‑of‑interest features.

    Parameters
    ----------
    data:
        Price data containing at least ``high`` and ``low`` columns.

    Returns
    -------
    Tuple[Dict[str, float], List[float]]
        ``enriched`` dictionary with ``support``, ``resistance`` and
        ``midpoint`` keys and a numeric ``vector`` of those values. When input
        data is missing or invalid, both outputs are empty.
    """
    df = _to_dataframe(data)
    if df.empty or not {"high", "low"}.issubset(df.columns):
        return {}, []

    support = float(df["low"].min())
    resistance = float(df["high"].max())
    midpoint = (support + resistance) / 2.0

    enriched = {"support": support, "resistance": resistance, "midpoint": midpoint}
    vector = [support, resistance, midpoint]
    return enriched, vector


__all__ = ["run"]
