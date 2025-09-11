"""ISPTS pipeline orchestrator service.

Consumes raw market data from Kafka, runs it through the ZanFlow v11
ISPTS stages, and publishes the enriched state to the configured
output topic.
"""
from __future__ import annotations

import json
import os
import signal
import traceback
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

import yaml
from confluent_kafka import Consumer, Producer, KafkaError
from pydantic import ValidationError
from confluent_kafka import Consumer, KafkaError, Producer

from core.predictive_scorer import PredictiveScorer
from core.session_journal import SessionJournal
from schemas.agent_profile_schemas import PipelineConfig, SessionManifest
from schemas import (
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

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
SESSION_MANIFEST = Path("session_manifest.yaml")
PIPELINE_PATH = Path("zanflow_v11_ispts_pipeline.json")


def _camel_to_snake(name: str) -> str:
    out = ""
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out += "_"
        out += ch.lower()
    return out


def _load_manifest() -> SessionManifest:
    try:
        data = yaml.safe_load(SESSION_MANIFEST.read_text(encoding="utf-8"))
        return SessionManifest.model_validate(data)
    except ValidationError as exc:
        print(f"manifest validation error: {exc}")
        raise ValueError("invalid session manifest") from exc


def _load_pipeline() -> List[str]:
    try:
        data = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
        pipeline = PipelineConfig.model_validate(data)
        return [stage.name for stage in pipeline.stages]
    except ValidationError as exc:
        print(f"pipeline validation error: {exc}")
        raise ValueError("invalid pipeline configuration") from exc


def _resolve_stage(name: str):
    module_name = f"analysis.{_camel_to_snake(name)}"
    module = import_module(module_name)
    if hasattr(module, "analyze"):
        return getattr(module, "analyze")
    if hasattr(module, "run"):
        return getattr(module, "run")
    if hasattr(module, "main"):
        return getattr(module, "main")
    raise AttributeError(f"No callable stage in {module_name}")


def main() -> None:
    try:
        manifest = _load_manifest()
        stages = _load_pipeline()
    except ValueError as exc:
        print(f"configuration error: {exc}")
        return

    topics = manifest.topics
    consume_topics = topics.consume
    produce_topic = topics.produce
    instrument_pair = manifest.instrument_pair
    timeframe = manifest.timeframe

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": os.getenv("ENRICHMENT_GROUP", "analysis-enrichment"),
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    consumer.subscribe(consume_topics)

    journal = SessionJournal(Path("session_journal.json"))
    shutdown = False

    def _handle_shutdown(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        while not shutdown:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"kafka error: {msg.error()}")
                continue

            tick = json.loads(msg.value().decode("utf-8"))
            state: Dict[str, Any] = {"tick": tick}
            success = True
            for stage_name in stages:
                try:
                    stage_fn = _resolve_stage(stage_name)
                    result = stage_fn(state)
                    state[stage_name] = result
                except Exception as exc:  # pragma: no cover - runtime logging
                    traceback.print_exc()
                    journal.append(
                        action="pipeline_stage",
                        decision=f"{stage_name}_failed",
                        error=str(exc),
                        instrument=instrument_pair,
                        timeframe=timeframe,
                    )
                    success = False
                    break
            if success:
                producer.produce(produce_topic, json.dumps(state).encode("utf-8"))
                journal.append(
                    action="pipeline_complete",
                    decision="success",
                    instrument=instrument_pair,
                    timeframe=timeframe,
                )
            consumer.commit(msg)
    finally:
        producer.flush()
        consumer.close()
        journal.flush()

                success = False
                break
        if success:
            scorer = PredictiveScorer()
            score = scorer.score(state)
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
                context_analyzer=state.get("ContextAnalyzer", {}),
                liquidity_engine=state.get("LiquidityEngine", {}),
                structure_validator=state.get("StructureValidator", {}),
                fvg_locator=state.get("FVGLocator", {}),
                risk_manager=state.get("RiskManager", {}),
                confluence_stacker=state.get("ConfluenceStacker", {}),
            )

            ts = tick.get("ts") or tick.get("timestamp")
            if isinstance(ts, (int, float)):
                timestamp = datetime.fromtimestamp(ts)
            else:
                timestamp = ts

            payload = UnifiedAnalysisPayloadV1(
                symbol=tick.get("symbol", instrument_pair),
                timeframe=tick.get("timeframe", timeframe),
                timestamp=timestamp,
                market_context=MarketContext(
                    symbol=tick.get("symbol", instrument_pair),
                    timeframe=tick.get("timeframe", timeframe),
                ),
                technical_indicators=TechnicalIndicators(),
                smc=SMCAnalysis(),
                wyckoff=WyckoffAnalysis(),
                microstructure=MicrostructureAnalysis(),
                predictive_analysis=predictive,
                ispts_pipeline=pipeline,
            )

            producer.produce(produce_topic, payload.model_dump_json().encode("utf-8"))
            journal.append(
                action="pipeline_complete",
                decision="success",
                instrument=instrument_pair,
                timeframe=timeframe,
            )
        consumer.commit(msg)


if __name__ == "__main__":  # pragma: no cover - service entry point
