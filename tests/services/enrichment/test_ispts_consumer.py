import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import BaseModel

# Stub out the broken `schemas` package with the minimal models required
class AnalysisPayload(BaseModel):
    symbol: str
    timeframe: str | None = None
    timestamp: int | float
    data: dict = {}

class PredictiveScorerResult(BaseModel):
    maturity_score: float = 0.0
    grade: str | None = None
    confidence_factors: list = []
    extras: dict = {}

class ConflictDetectionResult(BaseModel):
    is_conflict: bool

class PredictiveAnalysisResult(BaseModel):
    scorer: PredictiveScorerResult
    conflict_detection: ConflictDetectionResult

class ISPTSPipelineResult(BaseModel):
    context_analyzer: dict = {}
    liquidity_engine: dict = {}
    structure_validator: dict = {}
    fvg_locator: dict = {}
    risk_manager: dict = {}
    confluence_stacker: dict = {}

class MarketContext(BaseModel):
    symbol: str
    timeframe: str

class TechnicalIndicators(BaseModel):
    pass

class SMCAnalysis(BaseModel):
    pass

class WyckoffAnalysis(BaseModel):
    pass

class MicrostructureAnalysis(BaseModel):
    pass

class UnifiedAnalysisPayloadV1(BaseModel):
    symbol: str
    timeframe: str
    timestamp: object
    market_context: MarketContext
    technical_indicators: TechnicalIndicators
    smc: SMCAnalysis
    wyckoff: WyckoffAnalysis
    microstructure: MicrostructureAnalysis
    predictive_analysis: PredictiveAnalysisResult
    ispts_pipeline: ISPTSPipelineResult

schemas_module = ModuleType("schemas")
schemas_module.ISPTSPipelineResult = ISPTSPipelineResult
schemas_module.MarketContext = MarketContext
schemas_module.MicrostructureAnalysis = MicrostructureAnalysis
schemas_module.PredictiveAnalysisResult = PredictiveAnalysisResult
schemas_module.SMCAnalysis = SMCAnalysis
schemas_module.TechnicalIndicators = TechnicalIndicators
schemas_module.UnifiedAnalysisPayloadV1 = UnifiedAnalysisPayloadV1
schemas_module.WyckoffAnalysis = WyckoffAnalysis

behavioral_module = ModuleType("schemas.behavioral")
behavioral_module.AnalysisPayload = AnalysisPayload

predictive_module = ModuleType("schemas.predictive_schemas")
predictive_module.ConflictDetectionResult = ConflictDetectionResult
predictive_module.PredictiveScorerResult = PredictiveScorerResult

agent_profile_module = ModuleType("schemas.agent_profile_schemas")
class PipelineConfig(BaseModel):
    stages: list[str] = []
class SessionManifest(BaseModel):
    instrument_pair: str
    timeframe: str
    topics: object
agent_profile_module.PipelineConfig = PipelineConfig
agent_profile_module.SessionManifest = SessionManifest

sys.modules["schemas"] = schemas_module
sys.modules["schemas.behavioral"] = behavioral_module
sys.modules["schemas.predictive_schemas"] = predictive_module
sys.modules["schemas.agent_profile_schemas"] = agent_profile_module

from services.enrichment import ispts_consumer as ic


class FakeMessage:
    def __init__(self, payload: bytes):
        self._payload = payload

    def value(self):
        return self._payload

    def error(self):
        return None


class FakeConsumer:
    def __init__(self, *args, **kwargs):
        self.polled = 0
        self.committed = False

    def subscribe(self, topics):
        self.topics = topics

    def poll(self, timeout):
        if self.polled == 0:
            self.polled += 1
            payload = {
                "symbol": "EURUSD",
                "timeframe": "M1",
                "timestamp": 0,
                "data": {},
            }
            return FakeMessage(json.dumps(payload).encode("utf-8"))
        raise KeyboardInterrupt

    def commit(self, msg):
        self.committed = True

    def close(self):
        pass

    def list_topics(self, timeout=None):
        return SimpleNamespace()


class FakeProducer:
    def __init__(self, *args, **kwargs):
        self.produced = []

    def produce(self, topic, payload):
        self.produced.append((topic, payload))

    def flush(self):
        pass

    def list_topics(self, timeout=None):
        return SimpleNamespace()


class FakeScorer:
    def score(self, state):
        return {"maturity_score": 1.0, "grade": "A", "reasons": []}


class FakeJournal:
    def __init__(self, path):
        self.entries = []

    def append(self, **kwargs):
        self.entries.append(kwargs)

    def flush(self):
        pass


@pytest.fixture(autouse=True)
def reset_globals(monkeypatch):
    ic.consumer = None
    ic.producer = None
    monkeypatch.setattr(ic, "_run_server", lambda: None)
    monkeypatch.setattr(ic, "Consumer", FakeConsumer)
    monkeypatch.setattr(ic, "Producer", FakeProducer)
    monkeypatch.setattr(ic, "PredictiveScorer", FakeScorer)
    monkeypatch.setattr(ic, "SessionJournal", FakeJournal)
    monkeypatch.setattr(ic.signal, "signal", lambda *a, **k: None)
    yield


def run_main():
    try:
        ic.main()
    except KeyboardInterrupt:
        pass


def test_stage_order_and_success_publishes_output(monkeypatch):
    stages = ["StageOne", "StageTwo", "StageThree"]
    calls = []

    def stage_factory(name):
        def _stage(state):
            calls.append(name)
            return {"name": name}
        return _stage

    stage_map = {name: stage_factory(name) for name in stages}

    manifest = SimpleNamespace(
        instrument_pair="EURUSD",
        timeframe="M1",
        topics=SimpleNamespace(consume=["input"], produce="output"),
    )

    monkeypatch.setattr(ic, "_load_manifest", lambda: manifest)
    monkeypatch.setattr(ic, "_load_pipeline", lambda: stages)
    monkeypatch.setattr(ic, "_resolve_stage", lambda name: stage_map[name])

    run_main()

    assert calls == stages
    assert ic.producer.produced
    topic, payload = ic.producer.produced[0]
    assert topic == "output"
    data = json.loads(payload.decode("utf-8"))
    assert data["symbol"] == "EURUSD"


def test_stage_failure_stops_processing_and_journals(monkeypatch):
    stages = ["StageOne", "StageTwo", "StageThree"]
    calls = []

    def stage_one(state):
        calls.append("StageOne")
        return {"name": "StageOne"}

    def stage_two(state):
        calls.append("StageTwo")
        raise RuntimeError("boom")

    def stage_three(state):
        calls.append("StageThree")
        return {"name": "StageThree"}

    stage_map = {
        "StageOne": stage_one,
        "StageTwo": stage_two,
        "StageThree": stage_three,
    }

    manifest = SimpleNamespace(
        instrument_pair="EURUSD",
        timeframe="M1",
        topics=SimpleNamespace(consume=["input"], produce="output"),
    )

    journal = FakeJournal(None)

    monkeypatch.setattr(ic, "_load_manifest", lambda: manifest)
    monkeypatch.setattr(ic, "_load_pipeline", lambda: stages)
    monkeypatch.setattr(ic, "_resolve_stage", lambda name: stage_map[name])
    monkeypatch.setattr(ic, "SessionJournal", lambda path: journal)

    run_main()

    assert calls == ["StageOne", "StageTwo"]
    assert not ic.producer.produced
    assert journal.entries
    entry = journal.entries[0]
    assert entry["decision"] == "StageTwo_failed"
