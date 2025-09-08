import os
import json
import time
from typing import Dict, Any
from datetime import datetime, timezone

try:
    from confluent_kafka import Consumer, Producer  # type: ignore
except Exception:  # pragma: no cover
    Consumer = None  # type: ignore
    Producer = None  # type: ignore


BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
TOP_IN = os.getenv("TICKS_TOPIC", "ticks.BTCUSDT")
TOP_OUT = os.getenv("BARS_TOPIC", "bars.BTCUSDT.1m")
GROUP = os.getenv("KAFKA_GROUP", "bars-1m-builder")


def bucket_minute(ts: float) -> int:
    return int(ts // 60 * 60)


def main() -> None:
    if Consumer is None or Producer is None:
        print("confluent_kafka not available; exiting")
        return
    c = Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": GROUP,
        "auto.offset.reset": "latest",
    })
    p = Producer({"bootstrap.servers": BROKERS})
    c.subscribe([TOP_IN])
    agg: Dict[int, Dict[str, Any]] = {}
    try:
        while True:
            msg = c.poll(0.2)
            if msg is None:
                continue
            if msg.error():
                continue
            try:
                tick = json.loads(msg.value())
                ts = float(tick.get("ts") or time.time())
                price = float(tick["price"])  # required
                vol = float(tick.get("volume") or 0.0)
            except Exception:
                continue
            b = bucket_minute(ts)
            prev = b - 60
            bar = agg.get(b)
            if bar is None:
                agg[b] = bar = {"ts": b, "o": price, "h": price, "l": price, "c": price, "v": 0.0}
            bar["h"] = max(bar["h"], price)
            bar["l"] = min(bar["l"], price)
            bar["c"] = price
            bar["v"] += vol
            if prev in agg:
                out = agg.pop(prev)
                try:
                    p.produce(TOP_OUT, json.dumps(out).encode("utf-8"))
                except Exception:
                    pass
    finally:
        try:
            c.close()
        except Exception:
            pass
        try:
            p.flush(2.0)
        except Exception:
            pass


if __name__ == "__main__":
    main()

