"""Time utilities (local copy for MCP image)."""

import os
from typing import Union

import pandas as pd


LOCAL_TZ = os.getenv("TZ", "UTC")


def localize_tz(ts: Union[pd.Timestamp, int, float, str]) -> pd.Timestamp:
    """Convert a timestamp to the local timezone.

    Parameters
    ----------
    ts : Union[pd.Timestamp, int, float, str]
        Timestamp or value convertible to :class:`pandas.Timestamp`.

    Returns
    -------
    pd.Timestamp
        Timezone-aware timestamp converted to ``TZ`` environment setting
        (defaults to UTC).
    """
    if not isinstance(ts, pd.Timestamp):
        ts = pd.to_datetime(ts, utc=True)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(LOCAL_TZ)


__all__ = ["localize_tz"]

