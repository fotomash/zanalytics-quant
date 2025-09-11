from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisPayload(BaseModel):
    """Basic analysis payload transported via Kafka."""

    symbol: str = Field(..., description="Instrument identifier")
    timeframe: Optional[str] = Field(None, description="Associated timeframe, e.g., M15")
    timestamp: datetime = Field(..., description="Timestamp of the payload")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional analysis fields or raw tick data",
    )


class TradeExecutionEvent(BaseModel):
    """Trade execution event coming from execution systems."""

    trader_id: str = Field(..., description="Unique trader identifier")
    symbol: str = Field(..., description="Instrument traded")
    side: str = Field(..., description="Buy or sell side")
    quantity: float = Field(..., description="Executed quantity")
    price: float = Field(..., description="Execution price")
    timestamp: datetime = Field(..., description="Execution timestamp")
    extras: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event information"
    )


class BehavioralScoreOutput(BaseModel):
    """Behavioral score produced after evaluating trade history."""

    trader_id: str = Field(..., description="Unique trader identifier")
    score: float = Field(..., description="Behavioral score on 0-100 scale")
    passed: bool = Field(..., description="Whether behavioral checks passed")
    reasons: List[str] = Field(
        default_factory=list, description="Reasons or contributing factors"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Score generation time"
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict, description="Additional score details"
    )


__all__ = [
    "AnalysisPayload",
    "TradeExecutionEvent",
    "BehavioralScoreOutput",
]
