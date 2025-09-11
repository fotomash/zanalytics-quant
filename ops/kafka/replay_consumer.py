"""Simple Kafka consumer for replaying messages.

This script consumes a Kafka topic from a configurable start offset and
processes messages in batches. It is intended for replaying historical
bars or ticks into downstream stores such as Redis or Postgres for
analysis.

Configuration is provided via CLI arguments or environment variables:

- ``--topic`` / ``KAFKA_TOPIC`` – Kafka topic to consume.
- ``--start-offset`` / ``KAFKA_START_OFFSET`` – offset to begin replaying
  from (defaults to earliest).
- ``--batch-size`` / ``KAFKA_BATCH_SIZE`` – number of records to consume
  per poll.

Example usage:

.. code-block:: bash

    export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    export KAFKA_TOPIC=ticks.BTCUSDT
    python ops/kafka/replay_consumer.py --start-offset 0 --batch-size 100

Modify ``process_messages`` to push data into Redis or Postgres.
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable, Optional

import pyarrow as pa

from confluent_kafka import Consumer, KafkaError, TopicPartition


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
    """

    for msg in messages:
        if msg.error():
            if msg.error().code() != KafkaError._PARTITION_EOF:
                print(f"Kafka error: {msg.error()}")
            continue
        ticks = deserialize_ticks(msg.value())
        print(ticks)


def main() -> None:
    args = parse_args()
    if not args.topic:
        raise SystemExit("Kafka topic must be provided via --topic or KAFKA_TOPIC")

    consumer = create_consumer(args.bootstrap_servers, args.group_id)
    try:
        assign_start_offset(consumer, args.topic, args.start_offset)
        while True:
            batch = consumer.consume(args.batch_size, timeout=1.0)
            if not batch:
                break
            process_messages(batch)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
