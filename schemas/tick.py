from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class TickPayload(BaseModel):
    """Schema for an incoming market tick."""

    symbol: str = Field(..., description="Instrument identifier")
    bid: float = Field(..., description="Bid price")
    ask: float = Field(..., description="Ask price")
    volume: float = Field(..., description="Trade volume")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event time")


__all__ = ["TickPayload"]
