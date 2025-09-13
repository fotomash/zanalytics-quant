import json
from datetime import datetime

from services.enrichment import handler as h
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


class FakeRedis:
    def __init__(self):
        self.published = []

    def publish(self, channel, message):
        self.published.append((channel, message))


class DummyProducer:
    def __init__(self):
        self.produced = []

    def produce(self, topic, value):
        self.produced.append((topic, value))


class DummyConsumer:
    def commit(self, msg):
        self.committed = True


class DummyJournal:
    def append(self, **kwargs):
        pass


class DummyMessage:
    def __init__(self, payload: bytes):
        self._payload = payload

    def value(self):
        return self._payload


def _build_payload(score: float) -> UnifiedAnalysisPayloadV1:
    return UnifiedAnalysisPayloadV1(
        symbol="EURUSD",
        timeframe="1m",
        timestamp=datetime.utcnow(),
        market_context=MarketContext(symbol="EURUSD", timeframe="1m"),
        technical_indicators=TechnicalIndicators(),
        smc=SMCAnalysis(),
        wyckoff=WyckoffAnalysis(),
        microstructure=MicrostructureAnalysis(),
        predictive_analysis=PredictiveAnalysisResult(
            scorer=PredictiveScorerResult(maturity_score=score),
            conflict_detection=ConflictDetectionResult(is_conflict=False),
        ),
        ispts_pipeline=ISPTSPipelineResult(
            context_analyzer={},
            liquidity_engine={},
            structure_validator={},
            fvg_locator={},
            harmonic_processor={},
            risk_manager={},
            confluence_stacker={},
        ),
    )


def test_high_maturity_publishes_alert(monkeypatch):
    fake_payload = _build_payload(0.9)
    monkeypatch.setattr(h, "build_unified_analysis", lambda tick: fake_payload)

    fake_redis = FakeRedis()
    ctx = {
        "consumer": DummyConsumer(),
        "producer": DummyProducer(),
        "journal": DummyJournal(),
        "redis": fake_redis,
    }

    incoming = {
        "symbol": "EURUSD",
        "timeframe": "1m",
        "timestamp": 0,
        "data": {
            "strategy_name": "my_strategy",
            "direction": "long",
            "entry_price": 1.23,
        },
    }

    msg = DummyMessage(json.dumps(incoming).encode("utf-8"))

    h.on_message(ctx, msg)

    assert fake_redis.published
    channel, payload = fake_redis.published[0]
    assert channel == "discord-alerts"
    data = json.loads(payload)
    assert data["strategy_name"] == "my_strategy"
    assert data["symbol"] == "EURUSD"
    assert data["direction"] == "long"
    assert data["entry_price"] == 1.23
    assert "payload_id" in data

