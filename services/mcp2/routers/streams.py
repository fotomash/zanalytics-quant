from __future__ import annotations

from typing import Any, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import verify_api_key
from ..storage import redis_client


router = APIRouter(prefix="/streams", dependencies=[Depends(verify_api_key)])


def _normalize(entries: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry_id, data in entries:
        item = {"id": entry_id}
        item.update(data)
        out.append(item)
    return out


@router.get("/tick/{symbol}")
async def stream_ticks(
    symbol: str,
    count: int = Query(50, ge=1, le=500),
    start: str | None = Query(None, description="XRANGE start ID (inclusive)"),
    end: str | None = Query(None, description="XRANGE end ID (inclusive)"),
    reverse: bool = Query(True, description="Return latest first using XREVRANGE"),
):
    key = f"tick:{symbol}"
    r = redis_client.redis_streams
    try:
        if reverse:
            entries = await r.xrevrange(key, max="+", min="-", count=count)
        else:
            entries = await r.xrange(key, min=start or "-", max=end or "+", count=count)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"redis error: {exc}") from exc
    return {"key": key, "items": _normalize(entries)}


@router.get("/bar/{timeframe}/{symbol}")
async def stream_bars(
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"],
    symbol: str,
    count: int = Query(50, ge=1, le=500),
    reverse: bool = Query(True),
):
    key = f"bar:{timeframe}:{symbol}"
    r = redis_client.redis_streams
    try:
        entries = (
            await r.xrevrange(key, max="+", min="-", count=count)
            if reverse
            else await r.xrange(key, min="-", max="+", count=count)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"redis error: {exc}") from exc
    return {"key": key, "items": _normalize(entries)}
