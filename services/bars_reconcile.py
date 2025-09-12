import os
import json
from typing import Dict, Any

import redis
from services.common import get_logger

try:
    from confluent_kafka import Consumer, TopicPartition  # type: ignore
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore
    TopicPartition = None  # type: ignore


BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
TOPIC = os.getenv("BARS_TOPIC", "bars.BTCUSDT.1m")
PARTITION = int(os.getenv("KAFKA_PARTITION", "0"))
WINDOW_BARS = int(os.getenv("WINDOW_BARS", "1440"))  # last N bars

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_BARS_KEY = os.getenv("REDIS_BARS_KEY", "bars:BTCUSDT:1m")

# Tolerances
PIP_SIZE = float(os.getenv("PIP_SIZE", "0.0001"))
TICKS_TOL = int(os.getenv("TOL_PRICE_TICKS", "1"))
VOL_TOL = float(os.getenv("TOL_VOLUME", "1.0"))

logger = get_logger(__name__)


def read_kafka_last_n(topic: str, partition: int, n: int) -> Dict[int, Dict[str, Any]]:
    if Consumer is None or TopicPartition is None:
        return {}
    c = Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": "reconciler",
        "enable.auto.commit": False,
    })
    try:
        tp = TopicPartition(topic, partition)
        low, high = c.get_watermark_offsets(tp, cached=False)
        start = max(low, high - n)
        c.assign([TopicPartition(topic, partition, start)])
        out: Dict[int, Dict[str, Any]] = {}
        remain = high - start
        while remain > 0:
            msg = c.poll(0.2)
            if msg is None or msg.error():
                break
            remain -= 1
            try:
                obj = json.loads(msg.value())
                ts = int(obj.get("ts"))
                out[ts] = obj
            except Exception:
                continue
        return out
    finally:
        try:
            c.close()
        except Exception:
            pass


def read_redis_bars(key: str) -> Dict[int, Dict[str, Any]]:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        raw = r.get(key)
        if not raw:
            return {}
        arr = json.loads(raw)
        acc: Dict[int, Dict[str, Any]] = {}
        if isinstance(arr, list):
            for it in arr[-WINDOW_BARS:]:
                try:
                    ts = int(it.get("ts"))
                    acc[ts] = it
                except Exception:
                    continue
        elif isinstance(arr, dict):
            # Already keyed by ts
            for k, v in arr.items():
                try:
                    ts = int(k)
                    acc[ts] = v
                except Exception:
                    continue
        return acc
    except Exception:
        return {}


def within(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def main() -> None:
    kafka_bars = read_kafka_last_n(TOPIC, PARTITION, WINDOW_BARS)
    redis_bars = read_redis_bars(REDIS_BARS_KEY)
    if not kafka_bars or not redis_bars:
        logger.warning(
            "Missing bars from one of the sources; kafka=%d redis=%d",
            len(kafka_bars),
            len(redis_bars),
        )
    price_tol = PIP_SIZE * TICKS_TOL
    checked = 0
    mismatches = 0
    for ts, kb in sorted(kafka_bars.items()):
        rb = redis_bars.get(ts)
        if not rb:
            continue
        checked += 1
        try:
            if not (within(float(kb["o"]), float(rb["o"]), price_tol) and
                    within(float(kb["h"]), float(rb["h"]), price_tol) and
                    within(float(kb["l"]), float(rb["l"]), price_tol) and
                    within(float(kb["c"]), float(rb["c"]), price_tol) and
                    within(float(kb.get("v", 0.0)), float(rb.get("v", 0.0)), VOL_TOL)):
                mismatches += 1
        except Exception:
            mismatches += 1
    parity = 0.0 if checked == 0 else (1.0 - (mismatches / checked)) * 100.0
    logger.info(
        "Checked=%d mismatches=%d parity=%.3f%% tol_ticks=%d tol_vol=%s",
        checked,
        mismatches,
        parity,
        TICKS_TOL,
        VOL_TOL,
    )
    if parity < 99.9:
        logger.warning("PARITY BELOW THRESHOLD")
        exit(2)


if __name__ == "__main__":
    main()

