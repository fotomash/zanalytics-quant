"""Harmonic pattern processor utilities."""
from __future__ import annotations

from uuid import uuid4
from typing import Dict

import pandas as pd


def build_qdrant_payload(df: pd.DataFrame) -> Dict:
    """Attach a unique pattern identifier to ``df`` and create Qdrant payload.

    Parameters
    ----------
    df:
        DataFrame describing a harmonic pattern.

    Returns
    -------
    Dict
        Payload ready for Qdrant insertion. The unique ``pattern_id`` is
        serialized to a string and applied to both the DataFrame and payload.
    """
    if df.empty:
        return {}

    pattern_id = str(uuid4())
    df["pattern_id"] = pattern_id

    payload = {
        "pattern_id": pattern_id,
        "points": df.to_dict(orient="records"),
    }
    return payload
