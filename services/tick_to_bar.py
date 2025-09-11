    
import os
import json
import time
import redis
from datetime import datetime

# Define Redis client for tick_to_bar
r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, db=0)

VERSION_PREFIX = os.getenv("STREAM_VERSION_PREFIX", "v2")


def _minute_floor(ts: float) -> float:
    """Return the minute floor for a UNIX timestamp."""
    return (int(ts) // 60) * 60


def run(symbol: str, in_stream: str, out_stream: str, idle_flush: float = 3.0):
    state = None
    last_min = None
    last_id = "0-0"
    last_seen = time.time()

    while True:
        msgs = r.xread({in_stream: last_id}, block=1000, count=500)
        if msgs:
            _, entries = msgs[0]
            for msg_id, fields in entries:
                ts = float(fields.get(b"ts", time.time()))
                price = float(fields[b"mid"])
                vol = float(fields.get(b"tick_vol", 1.0))
                this_min = _minute_floor(ts)
                if last_min is None or this_min != last_min:
                    if state:
                        r.xadd(out_stream, {**state, "ts": state["ts"]})
                    state = {
                        "open": price,
                        "high": price,
                        "low": price,
                        "close": price,
                        "volume": vol,
                        "ts": this_min,
                    }
                    last_min = this_min
                else:
                    state["high"] = max(state["high"], price)
                    state["low"] = min(state["low"], price)
                    state["close"] = price
                    state["volume"] += vol
                last_id = msg_id
                last_seen = time.time()
        else:
            if state and (time.time() - last_seen) > idle_flush:
                r.xadd(out_stream, {**state, "ts": state["ts"]})
                state = None
            time.sleep(0.1)


if __name__ == "__main__":
    sym = os.getenv("SYMBOL", "EURUSD")
    run(symbol=sym, in_stream=f"{VERSION_PREFIX}:ticks:{sym}", out_stream=f"stream:bars:{sym}:1m")
