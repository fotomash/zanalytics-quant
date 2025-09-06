import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List

import pandas as pd
import redis
from celery import Celery

HOT_KEY_PREFIX = "ticks:hot:"
COLD_PATH = "/app/data/cold/"

app = Celery(
    "data_accumulator",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
redis_client = redis.Redis.from_url(app.conf.broker_url)


@app.task
def accumulate_ticks(symbol: str, new_ticks: List[Dict]) -> None:
    """Store live ticks in Redis with basic deduplication."""
    pipe = redis_client.pipeline()
    for tick in new_ticks:
        tick_str = f"{symbol}{tick['bid']}{tick['ask']}{tick['timestamp']}"
        tick_hash = hashlib.md5(tick_str.encode()).hexdigest()
        if redis_client.exists(f"tick_hash:{tick_hash}"):
            continue
        redis_client.setex(f"tick_hash:{tick_hash}", 3600, 1)
        pipe.rpush(f"{HOT_KEY_PREFIX}{symbol}", json.dumps(tick))
        pipe.ltrim(f"{HOT_KEY_PREFIX}{symbol}", -10000, -1)
    pipe.execute()


@app.task
def flush_to_cold(symbol: str) -> None:
    """Flush ticks from Redis to partitioned Parquet files."""
    key = f"{HOT_KEY_PREFIX}{symbol}"
    ticks_json = redis_client.lrange(key, 0, -1)
    if not ticks_json:
        return
    ticks = [json.loads(t) for t in ticks_json]
    df = pd.DataFrame(ticks)
    if df.empty:
        return
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    bars = df.resample("1min").agg({
        "bid": ["first", "last", "min", "max"],
        "ask": ["first", "last", "min", "max"],
    })
    bars.columns = [
        "bid_open",
        "bid_close",
        "bid_low",
        "bid_high",
        "ask_open",
        "ask_close",
        "ask_low",
        "ask_high",
    ]

    now = datetime.utcnow()
    partition_path = os.path.join(
        COLD_PATH,
        symbol,
        f"{now.year}",
        f"{now.month:02d}",
        f"{now.day:02d}.parquet",
    )
    os.makedirs(os.path.dirname(partition_path), exist_ok=True)

    if os.path.exists(partition_path):
        existing = pd.read_parquet(partition_path)
        bars = pd.concat([existing, bars])
    bars.to_parquet(partition_path, engine="pyarrow")
    redis_client.delete(key)
