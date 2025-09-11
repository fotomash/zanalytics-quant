from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketContext(BaseModel):
    """High level market information"""

    symbol: str
    timeframe: str
    session: Optional[str] = None
    trend: Optional[str] = None
    volatility: Optional[float] = None


class TechnicalIndicators(BaseModel):
    """Common technical indicator values"""

    rsi: Optional[float] = None
    macd: Optional[float] = None
    vwap: Optional[float] = None
    moving_averages: Dict[str, float] = Field(default_factory=dict)
    extras: Dict[str, float] = Field(default_factory=dict)


class SMCAnalysis(BaseModel):
    """Smart Money Concepts analysis"""

    market_structure: Optional[str] = None
    poi: List[str] = Field(default_factory=list)
    liquidity_pools: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class WyckoffAnalysis(BaseModel):
    """Wyckoff model state"""

    phase: Optional[str] = None
    events: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class MicrostructureAnalysis(BaseModel):
    """Order flow and microstructure metrics"""

    effective_spread: Optional[float] = None
    realized_spread: Optional[float] = None
    price_impact: Optional[float] = None
    liquidity_score: Optional[float] = None
    toxicity_score: Optional[float] = None


class BehavioralMetrics(BaseModel):
    """Trader behaviour or sentiment metrics"""

    sentiment: Optional[float] = None
    positioning: Optional[float] = None
    discipline: Optional[float] = None
    patience: Optional[float] = None
    notes: Optional[str] = None


class UnifiedAnalysisPayload(BaseModel):
    """Aggregate payload combining all analysis dimensions"""

    symbol: str
    timeframe: str
    timestamp: datetime
    market_context: MarketContext
    technical_indicators: TechnicalIndicators
    smc: SMCAnalysis
    wyckoff: WyckoffAnalysis
    microstructure: MicrostructureAnalysis
    behavioral: BehavioralMetrics
    extras: Dict[str, Any] = Field(default_factory=dict)
