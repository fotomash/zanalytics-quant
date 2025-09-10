"""Time utilities."""

import pandas as pd


def localize_tz(ts: pd.Timestamp) -> pd.Timestamp:
    """Convert a naive/UTC timestamp to America/New_York timezone."""
    return ts.tz_localize("UTC").tz_convert("America/New_York")
