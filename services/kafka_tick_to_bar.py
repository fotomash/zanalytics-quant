import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

import requests
from confluent_kafka import Consumer, KafkaException

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Configuration – adjust via env vars or a small config file if you prefer
# ----------------------------------------------------------------------
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_GROUP_ID = "pulsekernel-bar-consumer"
KAFKA_TOPIC = "mt5.ticks"
BAR_INTERVAL_SECONDS = 60  # 1‑minute bars (change as needed)
PULSE_API_URL = "http://localhost:8000/api/pulse/score"  # FastAPI endpoint
# ----------------------------------------------------------------------


class BarAggregator:
    """
    Simple in-memory bar builder. Keeps a dict per symbol with the
    current open/high/low/close and volume. When the interval expires,
    the bar is emitted and the bucket is reset.
    """

    def __init__(self, interval_seconds: int):
        self.interval = interval_seconds
        self.buckets = defaultdict(self._new_bucket)

    @staticmethod
    def _new_bucket():
        return {
            "open": None,
            "high": -float("inf"),
            "low": float("inf"),
            "close": None,
            "volume": 0,
            "start_ts": None,
        }

    def _reset_bucket(self, bucket, ts):
        bucket["open"] = bucket["high"] = bucket["low"] = bucket["close"] = None
        bucket["volume"] = 0
        bucket["start_ts"] = ts

    def add_tick(self, symbol: str, price: float, volume: float, ts: datetime):
        bucket = self.buckets[symbol]

        if bucket["start_ts"] is None:
            bucket["start_ts"] = ts
            bucket["open"] = price

        bucket["high"] = max(bucket["high"], price)
        bucket["low"] = min(bucket["low"], price)
        bucket["close"] = price
        bucket["volume"] += volume

        elapsed = (ts - bucket["start_ts"]).total_seconds()
        if elapsed >= self.interval:
            bar = {
                "symbol": symbol,
                "open": bucket["open"],
                "high": bucket["high"],
                "low": bucket["low"],
                "close": bucket["close"],
                "volume": bucket["volume"],
                "timestamp": bucket["start_ts"].isoformat(),
            }
            self._reset_bucket(bucket, ts)
            return bar
        return None


def make_consumer() -> Consumer:
    cfg = {
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": KAFKA_GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "enable.partition.eof": False,
        "session.timeout.ms": 30000,
        "max.poll.interval.ms": 300000,
    }
    consumer = Consumer(cfg)
    consumer.subscribe([KAFKA_TOPIC])
    return consumer


def post_bar_to_pulse(bar: dict):
    """Sends the aggregated bar to the PulseKernel FastAPI endpoint."""
    try:
        resp = requests.post(PULSE_API_URL, json=bar, timeout=5)
        resp.raise_for_status()
        log.debug(f"Bar posted: {bar['symbol']} @ {bar['timestamp']}")
    except Exception as exc:
        log.error(f"Failed to post bar {bar}: {exc}")


def run():
    consumer = make_consumer()
    aggregator = BarAggregator(BAR_INTERVAL_SECONDS)

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())

            tick = json.loads(msg.value().decode("utf-8"))
            symbol = tick["symbol"]
            price = float(tick["price"])
            volume = float(tick.get("volume", 0))
            ts_raw = tick.get("timestamp")
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_raw).replace(tzinfo=timezone.utc)

            bar = aggregator.add_tick(symbol, price, volume, ts)
            if bar:
                post_bar_to_pulse(bar)

    except KeyboardInterrupt:
        log.info("Graceful shutdown requested")
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
