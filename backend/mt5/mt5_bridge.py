"""Tick serialization utilities for MT5 bridge.

This module provides helpers to serialize tick data using the Arrow IPC
streaming format.  The resulting bytes can be published to Kafka and later
consumed by `ops.kafka.replay_consumer` which performs the reverse
operation.
"""
from __future__ import annotations

from typing import Iterable, Mapping

import pyarrow as pa


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
