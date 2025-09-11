"""Utilities for producing and consuming Kafka events.

Environment variables:
    KAFKA_BOOTSTRAP: Kafka bootstrap servers (default ``localhost:9092``)
    DATABASE_URL: Database connection string
    KAFKA_GROUP_ID: Default group id for :class:`KafkaConsumer` (default ``zanalyzer``)
"""

import os
import json
import pyarrow as pa
from confluent_kafka import Producer, Consumer, KafkaError

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "zanalyzer")
TOPIC_TRADES = "trades-stream"

def produce_trade(data):
    """Publish a trade event to Kafka."""
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP})
    producer.produce(TOPIC_TRADES, key=str(data['timestamp']), value=json.dumps(data))
    producer.flush()

def consume_trades(callback):
    """Consume trade events and invoke callback for each."""
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP,
        'group.id': 'enrichment-group',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe([TOPIC_TRADES])
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break
            data = json.loads(msg.value().decode('utf-8'))
            callback(data)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


import asyncio
from typing import AsyncIterator, Optional, Sequence


class KafkaConsumer(AsyncIterator[str]):
    """Asynchronous iterator over messages from Kafka topics.

    The consumer can subscribe to multiple topics, including wildcard
    patterns (e.g., ``"trades-*"``). Messages are yielded as UTF-8 strings.
    """

    def __init__(
        self,
        topics: Sequence[str],
        bootstrap_servers: Optional[str] = None,
        group_id: Optional[str] = None,
        poll_timeout: float = 1.0,
    ) -> None:
        self._config = {
            "bootstrap.servers": bootstrap_servers or KAFKA_BOOTSTRAP,
            "group.id": group_id or KAFKA_GROUP_ID,
            "auto.offset.reset": "earliest",
        }
        self._consumer = Consumer(self._config)
        self._consumer.subscribe(list(topics))
        self._poll_timeout = poll_timeout
        self._running = True

    def __aiter__(self) -> "KafkaConsumer":
        return self

    async def __anext__(self) -> str:
        while self._running:
            msg = await asyncio.to_thread(self._consumer.poll, self._poll_timeout)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(msg.error())
            return msg.value().decode("utf-8")
        raise StopAsyncIteration

    async def stop(self) -> None:
        """Stop consuming and close the underlying consumer."""
        if self._running:
            self._running = False
            await asyncio.to_thread(self._consumer.close)

    async def __aenter__(self) -> "KafkaConsumer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()


__all__ = [
    "produce_trade",
    "consume_trades",
    "KafkaConsumer",
]
