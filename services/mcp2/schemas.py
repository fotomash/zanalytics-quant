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
from backend.mcp.schemas import StrategyPayloadV1


class DocRecord(BaseModel):
    id: int
    content: str


__all__ = [
    "StrategyPayloadV1",
    "DocRecord",
    "MarketContext",
    "TechnicalIndicators",
    "SMCAnalysis",
    "WyckoffAnalysis",
    "MicrostructureAnalysis",
    "UnifiedAnalysisPayloadV1",
]
