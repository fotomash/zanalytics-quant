from datetime import datetime

from services.enrichment.dashboard_adapter import to_dashboard_payload
from schemas import (
    ConflictDetectionResult,
    HarmonicPattern,
    HarmonicResult,
    ISPTSPipelineResult,
    MarketContext,
    MicrostructureAnalysis,
    PredictiveAnalysisResult,
    PredictiveScorerResult,
    SMCAnalysis,
    TechnicalIndicators,
    UnifiedAnalysisPayloadV1,
    WyckoffAnalysis,
)


def _dummy_pipeline_result() -> ISPTSPipelineResult:
    return ISPTSPipelineResult(
        context_analyzer={},
        liquidity_engine={},
        structure_validator={},
        fvg_locator={},
        harmonic_processor={},
        risk_manager={},
        confluence_stacker={},
        harmonic=HarmonicResult(),
    )


def test_dashboard_payload_conversion() -> None:
    bars = [
        {
            "time": f"2024-01-01T00:0{i}:00",
            "open": i,
            "high": i + 0.5,
            "low": i - 0.5,
            "close": i,
        }
        for i in range(1, 6)
    ]

    pattern = HarmonicPattern(
        pattern="BAT",
        points=[{"index": i - 1, "price": float(i)} for i in range(1, 6)],
        prz={"min": 1.0, "max": 5.0},
        confidence=0.9,
    )

    payload = UnifiedAnalysisPayloadV1(
        symbol="EURUSD",
        timeframe="1m",
        timestamp=datetime.fromisoformat("2024-01-01T00:05:00"),
        market_context=MarketContext(symbol="EURUSD", timeframe="1m"),
        technical_indicators=TechnicalIndicators(),
        smc=SMCAnalysis(),
        wyckoff=WyckoffAnalysis(),
        microstructure=MicrostructureAnalysis(),
        harmonic=HarmonicResult(harmonic_patterns=[pattern]),
        predictive_analysis=PredictiveAnalysisResult(
            scorer=PredictiveScorerResult(
                maturity_score=0.0,
                grade=None,
                confidence_factors=[],
                extras={"components": {}, "details": {}},
            ),
            conflict_detection=ConflictDetectionResult(is_conflict=False),
        ),
        ispts_pipeline=_dummy_pipeline_result(),
    )

    result = to_dashboard_payload(payload, bars)
    assert result["symbol"] == "EURUSD"
    assert result["ohlc"][0]["time"] == bars[0]["time"]
    pattern_out = result["harmonic_patterns"][0]
    assert pattern_out["pattern_type"] == "BAT"
    assert pattern_out["point1_time"] == bars[0]["time"]
    assert pattern_out["point1_price"] == 1.0
    assert pattern_out["prz_low"] == 1.0
    assert pattern_out["prz_high"] == 5.0
