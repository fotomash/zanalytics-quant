"""Displacement/Structure-Shift (DSS) metrics."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


def compute_dss(df: pd.DataFrame) -> Tuple[Dict[str, float], np.ndarray]:
    """Derive displacement and structure-shift metrics.

    Parameters
    ----------
    df:
        DataFrame containing at least a ``close`` column. The index or
        ``timestamp`` column is not used, allowing callers to operate on raw
        sequences.  The function is deterministic and stateless so repeated
        calls on the same input return identical results.

    Returns
    -------
    Tuple[Dict[str, float], np.ndarray]
        A tuple ``(metrics, vector)`` where ``metrics`` summarises mean
        displacement and net structure shift.  ``vector`` is a ``(N, 2)`` array
        with displacement and shift for each row of ``df``.
    """
    if df is None or df.empty or "close" not in df.columns:
        return {}, np.empty((0, 2), dtype=float)

    close = df["close"].astype(float).to_numpy()

    # Displacement is simply the first discrete difference; prepend 0 so the
    # output aligns with the input length.
    displacement = np.diff(close, prepend=close[0])
    shift = np.sign(displacement)

    metrics = {
        "mean_displacement": float(displacement.mean()),
        "net_shift": float(shift.sum()),
    }

    vector = np.column_stack((displacement, shift)).astype(float)
    return metrics, vector


__all__ = ["compute_dss"]
