import os
import json
import asyncio
from typing import Optional

try:
    from aiokafka import AIOKafkaProducer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    AIOKafkaProducer = None  # type: ignore


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "mcp2.enriched_trades")

_producer: Optional["AIOKafkaProducer"] = None
_lock = asyncio.Lock()


async def _ensure_producer() -> Optional["AIOKafkaProducer"]:
    global _producer
    if not KAFKA_BOOTSTRAP_SERVERS or AIOKafkaProducer is None:
        return None
    if _producer is not None:
        return _producer
    async with _lock:
        if _producer is None:
            try:
                prod = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
                await prod.start()
                _producer = prod
            except Exception:
                _producer = None
    return _producer


async def send_trade(trade_id: str, payload: dict | str) -> None:
    """Send an enriched trade payload to Kafka if configured.

    Best-effort; silently no-op on config missing or errors.
    """
    prod = await _ensure_producer()
    if prod is None:
        return
    try:
        value = payload if isinstance(payload, str) else json.dumps(payload)
        await prod.send_and_wait(KAFKA_TOPIC, value=value.encode("utf-8"), key=trade_id.encode("utf-8"))
    except Exception:
        # best-effort; avoid crashing request path
        pass

