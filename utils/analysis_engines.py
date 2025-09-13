"""Utilities to build unified analysis payload.

Analyzer implementations previously lived here but have moved to
:mod:`core`. Only the :func:`build_unified_analysis` helper remains to
construct payloads for the enrichment service.
"""

from datetime import datetime

from components import advanced_stoploss_lots_engine, confluence_engine
from core.predictive_scorer import PredictiveScorer
from utils.enrichment_config import EnrichmentConfig, load_enrichment_config
from schemas.payloads import (
    ISPTSPipelineResult,
    MarketContext,
    MicrostructureAnalysis,
    HarmonicResult,
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


def build_unified_analysis(
    tick: dict, config: EnrichmentConfig | None = None
) -> "UnifiedAnalysisPayloadV1":
    """Run core analyzers and validate against the v1 unified analysis
    payload.

    Parameters
    ----------
    tick:
        Incoming market data.
    config:
        Optional :class:`~utils.enrichment_config.EnrichmentConfig` controlling
        which indicator groups are computed.  If ``None`` the default
        configuration is loaded from disk.
    """

    cfg = config or load_enrichment_config()

    confluence = {}
    if cfg.technical.enabled:
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
        harmonic=HarmonicResult(),
    )

    symbol = tick.get("symbol", "UNKNOWN")
    timeframe = tick.get("timeframe", "1m")
    ts = tick.get("ts") or tick.get("timestamp")
    if isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(ts)
    else:
        timestamp = ts

    smc = SMCAnalysis()
    wyckoff = WyckoffAnalysis()
    bars = tick.get("bars") or tick.get("data", {}).get("bars")

    if bars and cfg.structure.smc:
        try:  # pragma: no cover - optional dependency/data
            import pandas as pd
            from core.smc_analyzer import SMCAnalyzer

            smc_engine = SMCAnalyzer()
            smc_res = smc_engine.analyze(pd.DataFrame(bars))
            smc = SMCAnalysis(
                market_structure=smc_res.get("market_structure"),
                poi=[ob.get("type") for ob in smc_res.get("order_blocks", [])],
                liquidity_pools=[
                    zone.get("type") for zone in smc_res.get("liquidity_zones", [])
                ],
            )
        except Exception:
            pass

    harmonic_data = (
        tick.get("harmonic")
        or tick.get("data", {}).get("harmonic")
        or {}
    )
    if not harmonic_data:
        patterns = tick.get("harmonic_patterns") or tick.get("data", {}).get("harmonic_patterns")
        if patterns:
            harmonic_data["harmonic_patterns"] = patterns
    harmonic = HarmonicResult(**harmonic_data) if harmonic_data else HarmonicResult()
    pipeline.harmonic = harmonic

    if bars and cfg.structure.wyckoff:
        try:  # pragma: no cover - optional dependency/data
            import pandas as pd
            from core.wyckoff_analyzer import WyckoffAnalyzer

            wyckoff_engine = WyckoffAnalyzer()
            wyckoff_res = wyckoff_engine.analyze(pd.DataFrame(bars))
            wyckoff = WyckoffAnalysis(
                phase=wyckoff_res.get("current_phase"),
                events=[e.get("type") for e in wyckoff_res.get("events", [])],
            )
        except Exception:
            pass

    return UnifiedAnalysisPayloadV1(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        market_context=MarketContext(symbol=symbol, timeframe=timeframe),
        technical_indicators=TechnicalIndicators(extras=confluence),
        smc=smc,
        wyckoff=wyckoff,
        microstructure=MicrostructureAnalysis(),
        harmonic=harmonic,
        predictive_analysis=predictive,
        ispts_pipeline=pipeline,
        extras={"risk": risk},
    )
