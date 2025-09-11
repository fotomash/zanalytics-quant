import uuid
from fastapi import APIRouter, HTTPException, Query
from ..schemas import StrategyPayload, DocRecord
from ..storage import redis_client
from ..storage.pg import get_pool

router = APIRouter()


@router.post('/log_enriched_trade')
async def log_enriched_trade(payload: StrategyPayload):
    trade_id = str(uuid.uuid4())
    data = payload.model_dump_json()
    await redis_client.redis.set(redis_client.ns(f'payload:{trade_id}'), data)
    await redis_client.redis.lpush(redis_client.ns('trades'), trade_id)
    return {'id': trade_id}


@router.get('/search_docs', response_model=list[DocRecord])
async def search_docs(q: str = Query(..., alias='query')):
    pool = await get_pool()
    rows = await pool.fetch('SELECT id, content FROM docs WHERE content ILIKE $1', f'%{q}%')
    return [DocRecord(id=row['id'], content=row['content']) for row in rows]


@router.get('/fetch_payload', response_model=StrategyPayload)
async def fetch_payload(id: str):
    data = await redis_client.redis.get(redis_client.ns(f'payload:{id}'))
    if not data:
        raise HTTPException(status_code=404, detail='not found')
    return StrategyPayload.model_validate_json(data)


@router.get('/trades/recent', response_model=list[StrategyPayload])
async def recent_trades(limit: int = 10):
    ids = await redis_client.redis.lrange(redis_client.ns('trades'), 0, limit - 1)
    payloads = []
    for trade_id in ids:
        data = await redis_client.redis.get(redis_client.ns(f'payload:{trade_id}'))
        if data:
            payloads.append(StrategyPayload.model_validate_json(data))
    return payloads
