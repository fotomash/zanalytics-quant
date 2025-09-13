from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .predictive_schemas import ConflictDetectionResult, PredictiveScorerResult


class MarketContext(BaseModel):
    """High level market information"""

    symbol: str = Field(..., description="Instrument identifier")
    timeframe: str = Field(..., description="Timeframe of the context, e.g. 1m or 1h")
    session: Optional[str] = Field(
        None, description="Optional trading session label"
    )
    trend: Optional[str] = Field(
        None, description="Textual trend description such as bullish or bearish"
    )
    volatility: Optional[float] = Field(
        None, description="Volatility measure (e.g. ATR or custom metric)"
    )


class TechnicalIndicators(BaseModel):
    """Common technical indicator values"""

    rsi: Optional[float] = Field(
        None, description="Relative Strength Index value"
    )
    macd: Optional[float] = Field(
        None, description="Moving Average Convergence Divergence value"
    )
    vwap: Optional[float] = Field(
        None, description="Volume weighted average price"
    )
    moving_averages: Dict[str, float] = Field(
        default_factory=dict, description="Mapping of moving average name to value"
    )
    extras: Dict[str, float] = Field(
        default_factory=dict, description="Additional indicator values keyed by name"
    )


class SMCAnalysis(BaseModel):
    """Smart Money Concepts analysis"""

    market_structure: Optional[str] = Field(
        None, description="Market structure label such as bullish or bearish"
    )
    poi: List[str] = Field(
        default_factory=list, description="Points of interest discovered by the analysis"
    )
    liquidity_pools: List[str] = Field(
        default_factory=list, description="Identified liquidity pool identifiers"
    )
    notes: Optional[str] = Field(None, description="Free-form notes")


class WyckoffAnalysis(BaseModel):
    """Wyckoff model state"""

    phase: Optional[str] = Field(None, description="Current Wyckoff phase")
    events: List[str] = Field(
        default_factory=list, description="List of detected Wyckoff events"
    )
    notes: Optional[str] = Field(None, description="Optional notes")


class MicrostructureAnalysis(BaseModel):
    """Order flow and microstructure metrics"""

    effective_spread: Optional[float] = Field(
        None, description="Effective spread measure"
    )
    realized_spread: Optional[float] = Field(
        None, description="Realized spread measure"
    )
    price_impact: Optional[float] = Field(
        None, description="Price impact of trades"
    )
    liquidity_score: Optional[float] = Field(
        None, description="Derived liquidity score"
    )
    toxicity_score: Optional[float] = Field(
        None, description="Order flow toxicity score"
    )


class HarmonicPattern(BaseModel):
    """Detected harmonic pattern information."""

    pattern: str = Field(..., description="Name of the harmonic pattern")
    points: List[Dict[str, float]] = Field(
        default_factory=list,
        description="List of pivot points with index and price",
    )
    prz: Dict[str, float | None] = Field(
        default_factory=dict,
        description="Potential reversal zone boundaries",
    )
    confidence: float = Field(
        0.0, description="Confidence score for the pattern",
    )


class HarmonicResult(BaseModel):
    """Harmonic pattern detection results."""

    harmonic_patterns: List[HarmonicPattern] = Field(
        default_factory=list,
        description="List of detected harmonic patterns",
    )
    prz: Dict[str, float | None] = Field(
        default_factory=dict,
        description="Aggregated potential reversal zone boundaries",
    )
    confidence: float = Field(
        0.0,
        description="Aggregated confidence score",
    )


class PredictiveAnalysisResult(BaseModel):
    """Aggregated predictive scoring and conflict detection."""

    scorer: PredictiveScorerResult = Field(
        ..., description="Predictive maturity scoring output"
    )
    conflict_detection: ConflictDetectionResult = Field(
        ..., description="Directional conflict detection results"
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional predictive analysis fields",
    )


class ISPTSPipelineResult(BaseModel):
    """Outputs from each stage of the ISPTS pipeline."""

    context_analyzer: Any = Field(
        ..., description="Context analyzer stage output",
    )
    liquidity_engine: Any = Field(
        ..., description="Liquidity engine stage output",
    )
    structure_validator: Any = Field(
        ..., description="Structure validator stage output",
    )
    fvg_locator: Any = Field(
        ..., description="FVG locator stage output",
    )


class UnifiedAnalysisPayloadV1(BaseModel):
    """Version 1 unified analysis payload combining all analysis dimensions."""

    symbol: str = Field(..., description="Instrument identifier")
    timeframe: str = Field(
        ..., description="Timeframe used for the analysis, e.g. 1m or 1h"
    )
    timestamp: datetime = Field(..., description="Timestamp of the analysis snapshot")
    market_context: MarketContext = Field(
        ..., description="High level market information"
    )
    technical_indicators: TechnicalIndicators = Field(
        ..., description="Common technical indicator values"
    )
    smc: SMCAnalysis = Field(
        ..., description="Smart Money Concepts analysis results"
    )
    wyckoff: WyckoffAnalysis = Field(
        ..., description="Wyckoff model state"
    )
    microstructure: MicrostructureAnalysis = Field(
        ..., description="Order flow and microstructure metrics"
    )
    harmonic: HarmonicResult = Field(
        default_factory=HarmonicResult,
        description="Harmonic pattern detection results",
    )
    predictive_analysis: PredictiveAnalysisResult = Field(
        ..., description="Aggregated predictive scoring and conflict detection results",
    )
    ispts_pipeline: ISPTSPipelineResult = Field(
        ..., description="Outputs from each stage of the ISPTS pipeline",
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Unstructured additional fields for forward compatibility",
    )
