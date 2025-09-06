import numpy as np
import pandas as pd

REQUIRED = ["high", "low", "close", "volume"]


def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if "vwap" not in df.columns:
        pv = (df["high"] + df["low"] + df["close"]) / 3
        df["vwap"] = (pv * df["volume"]).cumsum() / df["volume"].replace(0, np.nan).cumsum()
    return df


def compute_confluence_indicators_df(latest_tick: dict) -> dict:
    """Placeholder implementation returning neutral score."""
    # In production, fetch cached bars and compute signals.
    return {"score": 0.0, "grade": "N", "reasons": [], "components": {}}
