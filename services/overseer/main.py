"""Simple Overseer service consuming from Kafka and logging messages."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from utils.kafka_utils import KafkaConsumer

KAFKA_TOPIC = os.getenv("OVERSEER_TOPIC", "overseer-events")


async def run() -> None:
    """Consume messages from ``OVERSEER_TOPIC`` and print them."""
    async with KafkaConsumer(KAFKA_TOPIC, group_id="overseer") as consumer:
        async for raw in consumer:
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            print(payload)


def main() -> None:
    """Entry point for running the overseer service."""
    asyncio.run(run())


__all__ = ["run", "main"]


if __name__ == "__main__":
    main()
