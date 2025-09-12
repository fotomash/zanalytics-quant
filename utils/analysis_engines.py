"""Utilities to build unified analysis payload.

Analyzer implementations previously lived here but have moved to
:mod:`core`. Only the :func:`build_unified_analysis` helper remains to
construct payloads for the enrichment service.
"""

from datetime import datetime

from components import advanced_stoploss_lots_engine, confluence_engine
from core.predictive_scorer import PredictiveScorer
from schemas.payloads import (
    ISPTSPipelineResult,
    MarketContext,
    MicrostructureAnalysis,
    PredictiveAnalysisResult,
    SMCAnalysis,
    TechnicalIndicators,
    UnifiedAnalysisPayloadV1,
    WyckoffAnalysis,
)
from schemas.predictive_schemas import (
    ConflictDetectionResult,
    PredictiveScorerResult,
)


def build_unified_analysis(tick: dict) -> "UnifiedAnalysisPayloadV1":
    """Run core analyzers and validate against the v1 unified analysis
    payload."""

    confluence = confluence_engine.compute_confluence_indicators_df(tick)
    risk = advanced_stoploss_lots_engine.compute_risk_snapshot(tick)

    scorer = PredictiveScorer()
    score = scorer.score(tick)
    predictive = PredictiveAnalysisResult(
        scorer=PredictiveScorerResult(
            maturity_score=score.get("maturity_score", 0.0),
            grade=score.get("grade"),
            confidence_factors=score.get("reasons", []),
            extras={
                "components": score.get("components", {}),
                "details": score.get("details", {}),
            },
        ),
        conflict_detection=ConflictDetectionResult(is_conflict=False),
    )

    pipeline = ISPTSPipelineResult(
        context_analyzer={},
        liquidity_engine={},
        structure_validator={},
        fvg_locator={},
        risk_manager={},
        confluence_stacker={},
    )

    symbol = tick.get("symbol", "UNKNOWN")
    timeframe = tick.get("timeframe", "1m")
    ts = tick.get("ts") or tick.get("timestamp")
    if isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(ts)
    else:
        timestamp = ts

    return UnifiedAnalysisPayloadV1(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        market_context=MarketContext(symbol=symbol, timeframe=timeframe),
        technical_indicators=TechnicalIndicators(extras=confluence),
        smc=SMCAnalysis(),
        wyckoff=WyckoffAnalysis(),
        microstructure=MicrostructureAnalysis(),
        predictive_analysis=predictive,
        ispts_pipeline=pipeline,
        extras={"risk": risk},
    )
