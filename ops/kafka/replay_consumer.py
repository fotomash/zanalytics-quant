"""Simple Kafka consumer for replaying messages.

This script consumes a Kafka topic from a configurable start offset and
processes messages in batches. It is intended for replaying historical
bars or ticks into downstream stores such as Redis or Postgres for
analysis.

The main entry point is :func:`main`, which is executed when invoking
``python ops/kafka/replay_consumer.py``.  Messages may be handled in two
ways:

``simple``
    Print each message to stdout (default).

``batch``
    Forward an entire batch of messages to a sink function.  Replace
    :func:`batch_sink` with custom logic to push data into Redis or
    Postgres.

Configuration is provided via CLI arguments or environment variables:

- ``--topic`` / ``KAFKA_TOPIC`` – Kafka topic to consume.
- ``--start-offset`` / ``KAFKA_START_OFFSET`` – offset to begin replaying
  from (defaults to earliest).
- ``--batch-size`` / ``KAFKA_BATCH_SIZE`` – number of records to consume
  per poll.
- ``--mode`` / ``KAFKA_CONSUMER_MODE`` – ``simple`` or ``batch``.

Example usage:

.. code-block:: bash

    export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    export KAFKA_TOPIC=ticks.BTCUSDT
    python ops/kafka/replay_consumer.py --start-offset 0 --batch-size 100

Customize :func:`batch_sink` to push payloads into Redis or Postgres.
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable, Optional

import pyarrow as pa

from confluent_kafka import Consumer, KafkaError, TopicPartition
try:  # pragma: no cover - module may be absent in tests
    from confluent_kafka import Consumer, KafkaError, TopicPartition
except Exception:  # pragma: no cover - fallback for environments without kafka
    Consumer = KafkaError = TopicPartition = None  # type: ignore


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments and merge with environment variables."""
    parser = argparse.ArgumentParser(description="Replay messages from a Kafka topic")
    parser.add_argument(
        "--topic",
        default=os.getenv("KAFKA_TOPIC", ""),
        help="Kafka topic to consume",
    )
    start_env = os.getenv("KAFKA_START_OFFSET")
    parser.add_argument(
        "--start-offset",
        type=int,
        default=int(start_env) if start_env else None,
        help="Offset to start consuming from (default: earliest)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("KAFKA_BATCH_SIZE", "100")),
        help="Number of messages to fetch per poll",
    )
    parser.add_argument(
        "--mode",
        choices=["simple", "batch"],
        default=os.getenv("KAFKA_CONSUMER_MODE", "simple"),
        help="Processing mode: simple prints each message; batch forwards the entire batch",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--group-id",
        default=os.getenv("KAFKA_GROUP_ID", "replay-consumer"),
        help="Kafka consumer group id",
    )
    return parser.parse_args()


def create_consumer(bootstrap_servers: str, group_id: str) -> Consumer:
    """Create a Confluent Kafka consumer."""
    return Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.partition.eof": True,
        }
    )


def assign_start_offset(consumer: Consumer, topic: str, start_offset: Optional[int]) -> None:
    """Assign the consumer to the requested start offset."""
    if start_offset is None:
        consumer.subscribe([topic])
        return

    metadata = consumer.list_topics(topic)
    partitions = [TopicPartition(topic, p, start_offset) for p in metadata.topics[topic].partitions]
    consumer.assign(partitions)


def deserialize_ticks(payload: bytes) -> list[dict]:
    """Deserialize Arrow IPC stream bytes into a list of tick dictionaries."""
    if not payload:
        return []
    reader = pa.ipc.open_stream(payload)
    table = reader.read_all()
    return table.to_pylist()


def process_messages(messages: Iterable) -> None:
    """Process a batch of Kafka messages.

    Replace the body of this function to forward data into Redis, Postgres,
    or another sink.  Messages are expected to contain Arrow IPC serialized
    ticks produced by ``backend.mt5.mt5_bridge.serialize_ticks``.

def print_messages(messages: Iterable) -> None:
    """Print each message value to stdout."""

    for msg in messages:
        if getattr(msg, "error", lambda: None)():
            err = msg.error()
            if KafkaError is None or err.code() != KafkaError._PARTITION_EOF:
                print(f"Kafka error: {err}")
            continue
        print(msg.value().decode("utf-8"))


def batch_sink(messages: Iterable) -> None:
    """Example batch sink that processes messages as a group.

    Replace the body of this function to forward data into Redis, Postgres,
    or another datastore.
    """

    valid = []
    for msg in messages:
        if getattr(msg, "error", lambda: None)():
            err = msg.error()
            if KafkaError is None or err.code() != KafkaError._PARTITION_EOF:
                print(f"Kafka error: {err}")
            continue
        ticks = deserialize_ticks(msg.value())
        print(ticks)
        valid.append(msg.value().decode("utf-8"))
    print(f"Batch size: {len(valid)}")


def consume(consumer: Consumer, batch_size: int, handler) -> None:
    """Consume batches from *consumer* and delegate to *handler*."""

    while True:
        batch = consumer.consume(batch_size, timeout=1.0)
        if not batch:
            break
        handler(batch)


def main() -> None:
    args = parse_args()
    if not args.topic:
        raise SystemExit("Kafka topic must be provided via --topic or KAFKA_TOPIC")

    consumer = create_consumer(args.bootstrap_servers, args.group_id)
    try:
        assign_start_offset(consumer, args.topic, args.start_offset)
        handler = batch_sink if args.mode == "batch" else print_messages
        consume(consumer, args.batch_size, handler)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
