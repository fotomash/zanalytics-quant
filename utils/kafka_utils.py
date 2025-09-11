from confluent_kafka import Producer, Consumer, KafkaError
import os
import json

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC_TRADES = 'trades-stream'

def produce_trade(data):
    """Publish a trade event to Kafka."""
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    producer.produce(TOPIC_TRADES, key=str(data['timestamp']), value=json.dumps(data))
    producer.flush()

def consume_trades(callback):
    """Consume trade events and invoke callback for each."""
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
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
from typing import AsyncIterator, Optional


class KafkaConsumer(AsyncIterator[str]):
    """Asynchronous iterator over messages from a Kafka topic."""

    def __init__(
        self,
        topic: str,
        bootstrap_servers: Optional[str] = None,
        group_id: str = "zanalyzer",
        poll_timeout: float = 1.0,
    ) -> None:
        self._config = {
            "bootstrap.servers": bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
        }
        self._consumer = Consumer(self._config)
        self._consumer.subscribe([topic])
        self._poll_timeout = poll_timeout
        self._loop = asyncio.get_event_loop()
        self._running = True

    def __aiter__(self) -> "KafkaConsumer":
        return self

    async def __anext__(self) -> str:
        if not self._running:
            raise StopAsyncIteration
        msg = await self._loop.run_in_executor(None, self._consumer.poll, self._poll_timeout)
        if msg is None:
            return await self.__anext__()
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                return await self.__anext__()
            raise RuntimeError(msg.error())
        return msg.value().decode("utf-8")

    async def stop(self) -> None:
        """Stop consuming and close the underlying consumer."""
        if self._running:
            self._running = False
            await self._loop.run_in_executor(None, self._consumer.close)

    async def __aenter__(self) -> "KafkaConsumer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()


__all__ = [
    "produce_trade",
    "consume_trades",
    "KafkaConsumer",
]
