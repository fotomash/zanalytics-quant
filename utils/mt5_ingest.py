"""Utilities for pulling ticks from MetaTrader5 and streaming to Kafka."""

import datetime
import logging
import os
import time
from typing import Callable, Optional

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


def get_tick_from_mt5(symbol: str) -> dict:
    """Retrieve the latest tick for ``symbol`` from MetaTrader5."""
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {symbol}")
        data = tick._asdict()
        # ``time`` is returned in seconds; normalisation happens later
        data["timestamp"] = data.get("time", 0)
        return data
    finally:
        mt5.shutdown()


def pull_and_stream(
    symbol: str = "EURUSD",
    from_time: Optional[datetime.datetime] = None,
    to_time: Optional[datetime.datetime] = None,
    tick_source: Optional[Callable[[str], dict]] = None,
) -> None:
    """Pull ticks from MT5 and stream them to Kafka.

    If ``from_time`` and ``to_time`` are provided, historical ticks for the
    supplied ``symbol`` are forwarded. Otherwise live ticks are pulled
    continuously using ``tick_source`` (defaults to :func:`get_tick_from_mt5`).
    """

    prod = _get_producer()
    source = tick_source or get_tick_from_mt5

    try:
        if from_time and to_time:
            if not mt5.initialize():
                raise RuntimeError("MT5 initialization failed")
            try:
                from_ms = int(from_time.timestamp() * 1000)
                to_ms = int(to_time.timestamp() * 1000)
                ticks = mt5.copy_ticks_range(symbol, from_ms, to_ms, mt5.COPY_TICKS_ALL)
            finally:
                mt5.shutdown()

            for t in ticks or []:
                tick = t._asdict()
                ts = tick.get("time_msc", tick.get("time", 0) * 1000)
                tick["timestamp"] = datetime.datetime.utcfromtimestamp(
                    ts / 1000
                ).isoformat()
                prod.send_tick(tick)
        else:
            while True:
                tick = source(symbol)
                ts = tick.get("timestamp")
                if isinstance(ts, (int, float)):
                    tick["timestamp"] = datetime.datetime.utcfromtimestamp(
                        ts
                    ).isoformat()
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
    """Flush pending messages and close the Kafka producer."""
    global _producer
    if _producer is None:
        return
    log.info("Flushing Kafka producer...")
    try:
        _producer.flush()
    finally:
        _producer.close()
    _producer = None
    log.info("Shutdown complete.")
