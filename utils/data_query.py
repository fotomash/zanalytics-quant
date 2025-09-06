import glob
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import redis

HOT_KEY_PREFIX = "ticks:hot:"
COLD_PATH = "/app/data/cold/"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)


def get_data(symbol: str, start_time: Optional[datetime] = None) -> pd.DataFrame:
    """Return combined hot and cold data for a symbol."""
    hot_key = f"{HOT_KEY_PREFIX}{symbol}"
    hot_ticks = [json.loads(t) for t in redis_client.lrange(hot_key, 0, -1)]
    df_hot = pd.DataFrame(hot_ticks)

    cold_glob = os.path.join(COLD_PATH, symbol, "*", "*", "*.parquet")
    cold_files = glob.glob(cold_glob)
    if cold_files:
        df_cold = pd.concat((pd.read_parquet(f) for f in cold_files), ignore_index=False)
    else:
        df_cold = pd.DataFrame()

    df = pd.concat([df_cold, df_hot], ignore_index=True)
    if start_time is not None and not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df[df["timestamp"] >= start_time]
    return df
