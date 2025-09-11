import os
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.mcp.schemas import StrategyPayloadV1
from ..schemas import DocRecord
from ..storage import redis_client
from ..storage.pg import get_pool
from ..auth import verify_api_key
from ..kafka_producer import send_trade

router = APIRouter(dependencies=[Depends(verify_api_key)])

# Optional Kafka producer controlled by MCP2_ENABLE_KAFKA env flag
KAFKA_ENABLED = os.getenv("MCP2_ENABLE_KAFKA", "").lower() in {"1", "true", "yes"}
if KAFKA_ENABLED:
    try:
        from aiokafka import AIOKafkaProducer

        _producer: AIOKafkaProducer | None = None
        _producer_lock = asyncio.Lock()

        async def get_producer() -> AIOKafkaProducer:
            global _producer
            if _producer is None:
                async with _producer_lock:
                    if _producer is None:
                        bootstrap = os.getenv("MCP2_KAFKA_BOOTSTRAP", "localhost:9092")
                        _producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
                        await _producer.start()
            return _producer

        @router.on_event("shutdown")
        async def _shutdown_producer() -> None:
            if _producer is not None:
                await _producer.stop()

    except Exception:  # pragma: no cover - aiokafka optional
        KAFKA_ENABLED = False


@router.post('/log_enriched_trade')
async def log_enriched_trade(payload: StrategyPayloadV1):
    trade_id = str(uuid.uuid4())
    data = payload.model_dump_json()
    await redis_client.redis.set(redis_client.ns(f'payload:{trade_id}'), data)
    await redis_client.redis.lpush(redis_client.ns('trades'), trade_id)
    if KAFKA_ENABLED:
        producer = await get_producer()
        await producer.send_and_wait("mcp2.enriched_trades", data.encode())

    try:
        await send_trade(trade_id, payload.model_dump())
    except Exception:
        # Kafka is best-effort; ignore failures
        pass
    return {'id': trade_id}


@router.get('/search_docs', response_model=list[DocRecord])
async def search_docs(q: str = Query(..., alias='query')):
    pool = await get_pool()
    rows = await pool.fetch('SELECT id, content FROM docs WHERE content ILIKE $1', f'%{q}%')
    return [DocRecord(id=row['id'], content=row['content']) for row in rows]


@router.get('/fetch_payload', response_model=StrategyPayloadV1)
async def fetch_payload(id: str):
    data = await redis_client.redis.get(redis_client.ns(f'payload:{id}'))
    if not data:
        raise HTTPException(status_code=404, detail='not found')
    return StrategyPayloadV1.model_validate_json(data)


@router.get('/trades/recent', response_model=list[StrategyPayloadV1])
async def recent_trades(limit: int = 10):
    ids = await redis_client.redis.lrange(redis_client.ns('trades'), 0, limit - 1)
    payloads = []
    for trade_id in ids:
        data = await redis_client.redis.get(redis_client.ns(f'payload:{trade_id}'))
        if data:
            payloads.append(StrategyPayloadV1.model_validate_json(data))
    return payloads
