from datetime import datetime

from pydantic import BaseModel

# Re-export unified analysis payloads
from schemas.payloads import (
    MarketContext,
    TechnicalIndicators,
    SMCAnalysis,
    WyckoffAnalysis,
    MicrostructureAnalysis,
    UnifiedAnalysisPayloadV1,
)


class StrategyPayload(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    date: datetime
    notes: str | None = None


class DocRecord(BaseModel):
    id: int
    content: str
