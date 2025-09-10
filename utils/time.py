
"""Time utilities."""

import pandas as pd
import os
from typing import Union
import pandas as pd

def localize_tz(ts: pd.Timestamp) -> pd.Timestamp:
    """Convert a naive/UTC timestamp to America/New_York timezone."""
    return ts.tz_localize("UTC").tz_convert("America/New_York")



LOCAL_TZ = os.getenv("TZ", "UTC")

def localize_tz(ts: Union[pd.Timestamp, int, float, str]) -> pd.Timestamp:
    """Convert a UTC timestamp to the local timezone.

    Parameters
    ----------
    ts: Union[pd.Timestamp, int, float, str]
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
