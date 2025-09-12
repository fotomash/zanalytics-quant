import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from utils.redis_client import get_redis_connection

COLD_ROOT = os.environ.get("COLD_ROOT", "/app/data/cold")
redis_client = get_redis_connection()


def get_ticks(symbol: str, start: datetime, end: Optional[datetime] = None) -> pd.DataFrame:
    """Return ticks for symbol between start and end using hot/cold storage."""
    end = end or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    frames = []
    if start >= now - timedelta(days=1):
        hot_key = f"ticks:hot:{symbol}"
        cached = redis_client.lrange(hot_key, 0, -1)
        if cached:
            df_hot = pd.DataFrame([json.loads(t) for t in cached])
            df_hot["timestamp"] = pd.to_datetime(df_hot["time"], unit="s", utc=True)
            mask = (df_hot["timestamp"] >= start) & (df_hot["timestamp"] <= end)
            frames.append(df_hot[mask])
    frames.append(_read_parquet_range(symbol, start, end))
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _read_parquet_range(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    try:
        import pyarrow.dataset as ds

        dataset = ds.dataset(
            f"{COLD_ROOT}/{symbol}",
            format="parquet",
            partitioning=["symbol", "date"],
        )
        table = dataset.to_table(
            filter=(ds.field("date") >= start.date()) & (ds.field("date") <= end.date())
        )
        df = table.to_pandas()
        if "timestamp" in df:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
            df = df[mask]
        return df
    except Exception:
        return pd.DataFrame()

def get_data(symbol: str, start_time: Optional[datetime] = None) -> pd.DataFrame:
    """Compatibility wrapper for previous API."""
    start = start_time or datetime.now(timezone.utc) - timedelta(days=1)
    return get_ticks(symbol, start)
