from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..storage import redis_client


router = APIRouter(prefix="/streams", dependencies=[Depends(verify_api_key)])


@router.get("/{stream}")
async def read_stream(stream: str, limit: int = Query(10, ge=1, le=100)):
    """Return recent entries from a Redis stream.

    Parameters
    ----------
    stream: str
        Name of the stream without namespace prefix.
    limit: int
        Maximum number of entries to return.
    """

    entries = await redis_client.xrange(stream)
    recent = entries[-limit:]
    return [{"id": entry_id, "fields": fields} for entry_id, fields in recent]


ALLOWED_TFS = {"1m", "5m", "15m", "1h", "4h", "1d"}
SYMBOL_RE = re.compile(r"^[A-Za-z0-9._:-]{3,24}$")


class TickItem(BaseModel):
    id: str
    ts_ms: int = Field(..., description="Timestamp (ms) from stream ID")
    ts_iso: str = Field(..., description="UTC ISO timestamp")
    symbol: str = Field(..., description="Instrument symbol")
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: float | None = None


class BarItem(BaseModel):
    id: str
    ts_ms: int
    ts_iso: str
    symbol: str = Field(..., description="Instrument symbol")
    timeframe: str = Field(..., description="Bar timeframe (e.g., 1m, 1h)")
    o: float | None = None
    h: float | None = None
    l: float | None = None
    c: float | None = None
    v: float | None = None


def _parse_ms_and_iso(entry_id: str) -> tuple[int, str]:
    try:
        ms = int(entry_id.split("-", 1)[0])
    except Exception:
        ms = 0
    iso = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return ms, iso


def _float_or_none(val: Any) -> float | None:
    try:
        if val is None:
            return None
        s = str(val).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def _normalize_ticks(entries: list[tuple[str, dict[str, Any]]], symbol: str) -> list[TickItem]:
    items: list[TickItem] = []
    for entry_id, data in entries:
        ts_ms, ts_iso = _parse_ms_and_iso(entry_id)
        bid = _float_or_none(data.get("bid"))
        ask = _float_or_none(data.get("ask"))
        last = _float_or_none(data.get("last") or data.get("price"))
        vol = _float_or_none(data.get("volume") or data.get("vol"))
        items.append(
            TickItem(
                id=entry_id,
                ts_ms=ts_ms,
                ts_iso=ts_iso,
                symbol=symbol,
                bid=bid,
                ask=ask,
                last=last,
                volume=vol,
            )
        )
    return items


def _normalize_bars(entries: list[tuple[str, dict[str, Any]]], symbol: str, timeframe: str) -> list[BarItem]:
    items: list[BarItem] = []
    for entry_id, data in entries:
        ts_ms, ts_iso = _parse_ms_and_iso(entry_id)
        # Support both long and short keys
        o = _float_or_none(data.get("open") or data.get("o"))
        h = _float_or_none(data.get("high") or data.get("h"))
        l = _float_or_none(data.get("low") or data.get("l"))
        c = _float_or_none(data.get("close") or data.get("c"))
        v = _float_or_none(data.get("volume") or data.get("v"))
        items.append(
            BarItem(
                id=entry_id,
                ts_ms=ts_ms,
                ts_iso=ts_iso,
                symbol=symbol,
                timeframe=timeframe,
                o=o,
                h=h,
                l=l,
                c=c,
                v=v,
            )
        )
    return items


def _validate_symbol(symbol: str) -> None:
    if not SYMBOL_RE.match(symbol):
        raise HTTPException(status_code=400, detail="invalid symbol")


@router.get("/tick/{symbol}", response_model=list[TickItem])
async def stream_ticks(
    symbol: str,
    count: int = Query(50, ge=1, le=500),
    start: str | None = Query(None, description="XRANGE start ID (inclusive)"),
    end: str | None = Query(None, description="XRANGE end ID (inclusive)"),
    reverse: bool = Query(True, description="Return latest first using XREVRANGE"),
):
    _validate_symbol(symbol)
    key = f"tick:{symbol}"
    r = redis_client.redis_streams
    try:
        if reverse:
            entries = await r.xrevrange(key, max="+", min="-", count=count)
        else:
            entries = await r.xrange(key, min=start or "-", max=end or "+", count=count)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"redis error: {exc}") from exc
    return _normalize_ticks(entries, symbol)


@router.get("/bar/{timeframe}/{symbol}", response_model=list[BarItem])
async def stream_bars(
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"],
    symbol: str,
    count: int = Query(50, ge=1, le=500),
    reverse: bool = Query(True),
):
    if timeframe not in ALLOWED_TFS:
        raise HTTPException(status_code=400, detail="invalid timeframe")
    _validate_symbol(symbol)

    # Prefer stream:bar:{tf}:{symbol}; fallback to bar:{tf}:{symbol}
    r = redis_client.redis_streams
    primary = f"stream:bar:{timeframe}:{symbol}"
    fallback = f"bar:{timeframe}:{symbol}"
    try:
        entries = await r.xrevrange(primary if reverse else primary, max="+", min="-", count=count) if reverse else await r.xrange(primary, min="-", max="+", count=count)
        if not entries:
            entries = await r.xrevrange(fallback if reverse else fallback, max="+", min="-", count=count) if reverse else await r.xrange(fallback, min="-", max="+", count=count)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"redis error: {exc}") from exc
    return _normalize_bars(entries, symbol, timeframe)
