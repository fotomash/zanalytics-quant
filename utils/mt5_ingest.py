import os
import time
import json
import logging
import datetime
from typing import Optional
import MetaTrader5 as mt5
from utils.mt5_kafka_producer import MT5KafkaProducer

log = logging.getLogger(__name__)

# Pull bootstrap address from env (default works for Docker compose)
bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

_producer: Optional[MT5KafkaProducer] = None


def _get_producer() -> MT5KafkaProducer:
    """Create the Kafka producer on first use."""
    global _producer
    if _producer is None:
        _producer = MT5KafkaProducer(bootstrap_servers=bootstrap)
    return _producer


def get_tick_from_mt5() -> dict:
    """Placeholder for actual MT5 tick retrieval."""
    raise NotImplementedError("Connect to MT5 and return a tick dictionary")



def pull_and_stream() -> None:
    """Pull ticks from MT5 and stream them to Kafka."""
    prod = _get_producer()
    try:
        while True:
            tick = get_tick_from_mt5()  # <-- your existing MT5 call
            # Normalise timestamp to ISO-8601 UTC
            ts = tick.get("timestamp")
            if isinstance(ts, (int, float)):
                tick["timestamp"] = datetime.datetime.utcfromtimestamp(ts).isoformat()
            else:
                tick["timestamp"] = datetime.datetime.utcnow().isoformat()

            prod.send_tick(tick)

            # Optional back-pressure: sleep a tiny bit if queue is large
            if prod.producer.len() > 5000:
                time.sleep(0.01)
    finally:
        try:
            prod.flush()
        finally:
            prod.close()


# Backwards compatibility
def stream_ticks() -> None:
    pull_and_stream()


def graceful_shutdown() -> None:
def pull_and_stream(symbol: str, from_time: datetime.datetime, to_time: datetime.datetime):
    """Pull historical MT5 ticks for ``symbol`` and forward them to Kafka."""
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")
    try:
        # MetaTrader5 requires time values as integer milliseconds since the epoch
        from_ms = int(from_time.timestamp() * 1000)
        to_ms = int(to_time.timestamp() * 1000)
        ticks = mt5.copy_ticks_range(symbol, from_ms, to_ms, mt5.COPY_TICKS_ALL)
    finally:
        mt5.shutdown()

    for t in ticks or []:
        tick = t._asdict()
        ts = tick.get("time_msc", tick.get("time", 0) * 1000)
        tick["timestamp"] = datetime.datetime.utcfromtimestamp(ts / 1000).isoformat()
        producer.send_tick(tick)


def graceful_shutdown():
    """Flush pending messages before exiting."""
    if _producer is None:
        return
    log.info("Flushing Kafka producer...")
    try:
        _producer.flush()
    finally:
        _producer.close()
    log.info("Shutdown complete.")
