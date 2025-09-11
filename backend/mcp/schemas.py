from __future__ import annotations

"""Shared pydantic schemas for strategy payloads."""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class MarketContext(BaseModel):
    """High level market information."""

    symbol: str = Field(..., description="Instrument identifier")
    timeframe: str = Field(..., description="Timeframe of the context, e.g. 1m or 1h")
    session: Optional[str] = Field(
        None, description="Optional trading session label"
    )


class Features(BaseModel):
    """Arbitrary feature values used by the strategy."""

    indicators: Dict[str, float] = Field(
        default_factory=dict, description="Mapping of feature name to value"
    )
    notes: Optional[str] = Field(None, description="Free-form notes about features")


class RiskConfig(BaseModel):
    """Risk management configuration."""

    max_risk_per_trade: Optional[float] = Field(
        None, description="Maximum risk per trade as a fraction of equity"
    )
    max_positions: Optional[int] = Field(
        None, description="Maximum simultaneous open positions"
    )
    max_daily_drawdown: Optional[float] = Field(
        None, description="Maximum allowed daily drawdown"
    )


class PositionsSummary(BaseModel):
    """Summary of current positions when the payload was generated."""

    open: int = Field(0, description="Number of open positions")
    closed: int = Field(0, description="Number of recently closed positions")
    total_risk: Optional[float] = Field(
        None, description="Aggregate risk exposure across open positions"
    )


class StrategyPayloadV1(BaseModel):
    """Strategy payload schema version 1."""

    strategy: str = Field(..., description="Name of the trading strategy")
    timestamp: datetime = Field(..., description="Payload creation timestamp")
    market: MarketContext = Field(..., description="High level market information")
    features: Features = Field(
        default_factory=Features, description="Indicator or feature values"
    )
    risk: RiskConfig = Field(
        default_factory=RiskConfig, description="Risk management configuration"
    )
    positions: PositionsSummary = Field(
        default_factory=PositionsSummary, description="Summary of positions"
    )


__all__ = [
    "MarketContext",
    "Features",
    "RiskConfig",
    "PositionsSummary",
    "StrategyPayloadV1",
]
