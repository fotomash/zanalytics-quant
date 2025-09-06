from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


class BarIn(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


@router.post("/score")
async def receive_bar(bar: BarIn):
    """Entry point for Kafka‑aggregated bars."""
    try:
        from core.pulse_kernel import process_bar  # adjust import as needed

        await process_bar(bar.dict())
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - simple passthrough
        raise HTTPException(status_code=500, detail=str(exc))
