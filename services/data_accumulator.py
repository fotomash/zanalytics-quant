import os
import json
import pandas as pd
import redis
from celery import Celery
from datetime import datetime
from typing import List, Dict
import hashlib  # For deduplication
from pyarrow import parquet as pq  # For cold storage

# Celery setup (integrate with Django: app = Celery('zanalytics', broker='redis://redis:6379/0')
app = Celery('data_accumulator', broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
redis_client = redis.Redis.from_url(app.conf.broker_url)

HOT_KEY_PREFIX = "ticks:hot:"  # e.g., "ticks:hot:EURUSD"
COLD_PATH = "/app/data/cold/"  # Partitioned Parquet dir

@app.task
def accumulate_ticks(symbol: str, new_ticks: List[Dict]):
    """Ingest live ticks, deduplicate, store in hot (Redis), enrich if needed."""
    pipe = redis_client.pipeline()
    for tick in new_ticks:
        # Deduplication hash
        tick_str = f"{symbol}{tick['bid']}{tick['ask']}{tick['timestamp']}"
        tick_hash = hashlib.md5(tick_str.encode()).hexdigest()
        if redis_client.exists(f"tick_hash:{tick_hash}"):
            continue  # Duplicate
        redis_client.setex(f"tick_hash:{tick_hash}", 3600, 1)  # 1-hour expire

        # Store in hot Redis list (last 10k ticks; FIFO)
        pipe.rpush(f"{HOT_KEY_PREFIX}{symbol}", json.dumps(tick))
        pipe.ltrim(f"{HOT_KEY_PREFIX}{symbol}", -10000, -1)  # Keep last 10k
    pipe.execute()

@app.task
def flush_to_cold(symbol: str):
    """Periodic flush: Aggregate hot ticks to cold Parquet (e.g., hourly bars)."""
    ticks_json = redis_client.lrange(f"{HOT_KEY_PREFIX}{symbol}", 0, -1)
    if not ticks_json:
        return

    ticks = [json.loads(t) for t in ticks_json]
    df = pd.DataFrame(ticks)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Aggregate to M1 bars (example enrichment)
    bars = df.resample('1min').agg({
        'bid': ['first', 'last', 'min', 'max'],
        'ask': ['first', 'last', 'min', 'max']
    })
    bars.columns = ['bid_open', 'bid_close', 'bid_low', 'bid_high', 'ask_open', 'ask_close', 'ask_low', 'ask_high']

    # Partitioned Parquet path (e.g., /data/cold/EURUSD/2025/09/06.parquet)
    now = datetime.now()
    partition_path = f"{COLD_PATH}{symbol}/{now.year}/{now.month:02d}/{now.day:02d}.parquet"
    os.makedirs(os.path.dirname(partition_path), exist_ok=True)

    # Append or write
    if os.path.exists(partition_path):
        existing = pd.read_parquet(partition_path)
        bars = pd.concat([existing, bars])
    bars.to_parquet(partition_path)

    # Clear hot after flush (or trim older)
    redis_client.delete(f"{HOT_KEY_PREFIX}{symbol}")

# Usage: In Django/MT5 view, after ingestion: accumulate_ticks.delay('EURUSD', new_ticks_list)
# Schedule flush: Celery beat every hour: flush_to_cold.delay('EURUSD')
