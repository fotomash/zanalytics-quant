"""Tick serialization utilities for MT5 bridge.

This module provides helpers to serialize tick data using the Arrow IPC
streaming format.  The resulting bytes can be published to Kafka and later
consumed by `ops.kafka.replay_consumer` which performs the reverse
operation.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, Mapping

import pyarrow as pa
import redis

try:  # pragma: no cover - MetaTrader5 may not be available
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - handled gracefully if missing
    mt5 = None


def serialize_ticks(ticks: Iterable[Mapping]) -> bytes:
    """Serialize an iterable of tick mappings to Arrow IPC stream bytes.

    Parameters
    ----------
    ticks:
        Iterable of mappings representing individual ticks.  Each mapping
        should contain primitive values (ints, floats, strings, etc.) and all
        ticks are expected to share the same keys.

    Returns
    -------
    bytes
        The Arrow IPC streaming representation of the ticks.
    """
    # Convert the iterable of dict-like objects into an Arrow table
    tick_list = list(ticks)
    if not tick_list:
        return b""
    table = pa.Table.from_pylist(tick_list)

    # Serialize using a BufferOutputStream and Arrow's streaming writer
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)

    return sink.getvalue().to_pybytes()


# MT5 Tick Bridge
# ===============
#
# Simple bridge for publishing MetaTrader 5 tick data to a Redis stream.
#
# Tick message schema published to Redis stream:
#
# {
#     "symbol": "<string>",    # e.g., "EURUSD"
#     "time": "<ISO8601>",     # timestamp of the quote
#     "bid": <float>,          # bid price
#     "ask": <float>           # ask price
# }
#
# Each message is stored in the Redis stream under the field "tick" as a
# JSON encoded string. Downstream consumers should decode the field using
# ``json.loads``.


class MT5Bridge:
    """Publish MT5 ticks to a Redis stream using JSON serialization."""

    def __init__(
        self,
        stream_name: str,
        redis_url: str = "redis://localhost:6379/0",
    ) -> None:
        self.stream_name = stream_name
        self.redis = redis.from_url(redis_url)

    def publish_tick(self, symbol: str) -> None:
        """Fetch latest tick for ``symbol`` and publish to the Redis stream."""
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available")

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return

        tick_data: Dict[str, Any] = {
            "symbol": symbol,
            "time": datetime.fromtimestamp(tick.time).isoformat(),
            "bid": tick.bid,
            "ask": tick.ask,
        }

        # Publish the tick as JSON so consumers get a well-defined schema
        self.redis.xadd(self.stream_name, {"tick": json.dumps(tick_data)})
