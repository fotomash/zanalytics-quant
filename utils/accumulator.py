import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import redis
from celery import shared_task

from utils.data_processor import resample_ticks_to_bars
from journal_engine import log_event, check_tick_gaps

COLD_ROOT = os.environ.get("COLD_ROOT", "/app/data/cold")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

@shared_task(bind=True, max_retries=3)
def flush_and_aggregate(self, symbol: str, raw_ticks: Optional[List[Dict]] = None):
    """Aggregate ticks from Redis and flush to partitioned Parquet."""
    try:
        if raw_ticks is None:
            hot_key = f"ticks:hot:{symbol}"
            cache = redis_client.lrange(hot_key, 0, -1)
            raw_ticks = [json.loads(t) for t in cache]
            if cache:
                redis_client.delete(hot_key)
        df = enrich_and_dedupe(raw_ticks or [])
        if df.empty:
            return {"status": "skipped", "reason": "no data"}

        check_tick_gaps(symbol, df)
        bars = resample_ticks_to_bars(df, freqs=["1T", "5T", "15T"])

        now = datetime.now(timezone.utc)
        path = f"{COLD_ROOT}/{symbol}/{now.year}/{now.month:02d}"
        os.makedirs(path, exist_ok=True)
        file = f"{path}/{now.day:02d}.parquet"

        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, file)

        log_event({
            "event": "accumulator_flush",
            "symbol": symbol,
            "tick_count": len(df),
            "bar_count": {k: len(v) for k, v in bars.items()},
            "output_file": file,
            "timestamp": now.isoformat(),
        })
        return {"status": "success", "file": file, "ticks": len(df)}
    except Exception as exc:
        self.retry(countdown=60, exc=exc)

def enrich_and_dedupe(ticks: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(ticks)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["date"] = df["timestamp"].dt.date
    if "symbol" not in df:
        df["symbol"] = "UNKNOWN"

    hash_input = (
        df[["timestamp", "bid", "ask"]]
        .astype(str)
        .agg("-".join, axis=1)
    )
    df["hash"] = hash_input.apply(lambda s: hashlib.md5(s.encode()).hexdigest())
    df = df.drop_duplicates(subset="hash")

    df["toxicity"] = (df["ask"] - df["bid"]).abs() / df["bid"]
    df["liq_score"] = 1 - df["toxicity"]
    df["regime_vol"] = df["ask"].rolling(100).std()
    return df.drop(columns=["hash"])
