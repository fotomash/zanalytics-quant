from datetime import datetime

from services.enrichment.dashboard_payload import build_harmonic_dashboard_payload
from schemas.payloads import (
    HarmonicResult,
    ISPTSPipelineResult,
    MarketContext,
    MicrostructureAnalysis,
    PredictiveAnalysisResult,
    PredictiveScorerResult,
    ConflictDetectionResult,
    SMCAnalysis,
    TechnicalIndicators,
    UnifiedAnalysisPayloadV1,
    WyckoffAnalysis,
)


def make_payload() -> UnifiedAnalysisPayloadV1:
    pattern = {
        "pattern": "bat",
        "points": [
            {"index": 0, "price": 1.0},
            {"index": 1, "price": 1.1},
            {"index": 2, "price": 1.2},
            {"index": 3, "price": 1.1},
        ],
        "prz": {"low": 0.9, "high": 1.3},
        "confidence": 0.8,
    }
    return UnifiedAnalysisPayloadV1(
        symbol="EURUSD",
        timeframe="1m",
        timestamp=datetime(2023, 1, 1),
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
        ispts_pipeline=ISPTSPipelineResult(
            context_analyzer={},
            liquidity_engine={},
            structure_validator={},
            fvg_locator={},
        ),
        extras={},
    )


def test_build_harmonic_dashboard_payload() -> None:
    payload = make_payload()
    bars = [
        {"time": "2023-01-01T00:00:00Z", "open": 1, "high": 1, "low": 1, "close": 1},
        {"time": "2023-01-01T00:01:00Z", "open": 1, "high": 1, "low": 1, "close": 1},
        {"time": "2023-01-01T00:02:00Z", "open": 1, "high": 1, "low": 1, "close": 1},
        {"time": "2023-01-01T00:03:00Z", "open": 1, "high": 1, "low": 1, "close": 1},
    ]

    result = build_harmonic_dashboard_payload(payload, bars)

    assert result["symbol"] == "EURUSD"
    assert result["ohlc"] == bars

    pattern = result["harmonic_patterns"][0]
    assert pattern["pattern_type"] == "bat"
    assert pattern["point1_time"] == bars[0]["time"]
    assert pattern["point3_price"] == 1.2
    assert pattern["prz_low"] == 0.9
    assert pattern["prz_high"] == 1.3
