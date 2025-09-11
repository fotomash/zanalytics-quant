"""ISPTS pipeline orchestrator service.

Consumes raw market data from Kafka, runs it through the ZanFlow v11
ISPTS stages, and publishes the enriched state to the configured output
topic. A lightweight FastAPI server exposes health and metrics endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from datetime import datetime
from enum import Enum
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

import uvicorn
import yaml
from confluent_kafka import Consumer, KafkaError, Producer
from fastapi import FastAPI, Response
from pydantic import ValidationError
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from schemas.behavioral import AnalysisPayload

from core.predictive_scorer import PredictiveScorer
from core.session_journal import SessionJournal
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
from schemas.agent_profile_schemas import PipelineConfig, SessionManifest
from schemas.predictive_schemas import ConflictDetectionResult, PredictiveScorerResult

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
SESSION_MANIFEST = Path("session_manifest.yaml")
PIPELINE_PATH = Path("zanflow_v11_ispts_pipeline.json")

app = FastAPI()

consumer: Consumer | None = None
producer: Producer | None = None

logger = logging.getLogger(__name__)

enriched_payloads_processed_total = Counter(
    "enriched_payloads_processed_total",
    "Total number of enriched payloads processed",
)
processing_latency_seconds = Histogram(
    "processing_latency_seconds",
    "Time spent processing each payload in seconds",
)


class HealthStatus(str, Enum):
    healthy = "healthy"
    unhealthy = "unhealthy"


@app.get("/health")
def health() -> Dict[str, HealthStatus]:
    """Check Kafka connectivity and return service health."""
    status = HealthStatus.healthy
    try:
        if consumer is None or producer is None:
            raise RuntimeError("Kafka not initialized")
        consumer.list_topics(timeout=1.0)
        producer.list_topics(timeout=1.0)
    except Exception:  # pragma: no cover - network I/O
        status = HealthStatus.unhealthy
    return {"status": status}


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
        manifest = SessionManifest.model_validate(data)
        logger.info("session prompt_version=%s", manifest.prompt_version)
        return manifest
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        logger.error("manifest validation error: %s", exc)
        raise ValueError("invalid session manifest") from exc


def _load_pipeline() -> List[str]:
    try:
        data = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
        pipeline = PipelineConfig.model_validate(data)
        return [stage.name for stage in pipeline.stages]
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.error("pipeline validation error: %s", exc)
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


def _run_server() -> None:
    """Run the FastAPI server in a thread."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )


def main() -> None:
    global consumer, producer

    try:
        manifest = _load_manifest()
        stages = _load_pipeline()
    except ValueError as exc:
        logger.error("configuration error: %s", exc)
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

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    journal = SessionJournal(Path("session_journal.json"))
    shutdown = threading.Event()

    def _handle_shutdown(signum, frame):
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        while not shutdown.is_set():
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("kafka error: %s", msg.error())
                continue

            start_time = time.perf_counter()
            tick = json.loads(msg.value().decode("utf-8"))
            try:
                incoming = AnalysisPayload.model_validate_json(
                    msg.value().decode("utf-8")
                )
            except ValidationError as exc:
                logger.error("payload validation error: %s", exc)
                consumer.commit(msg)
                continue

            tick = incoming.model_dump()
            state: Dict[str, Any] = {"tick": tick}
            success = True
            for stage_name in stages:
                try:
                    stage_fn = _resolve_stage(stage_name)
                    result = stage_fn(state)
                    state[stage_name] = result
                except Exception as exc:  # pragma: no cover - runtime logging
                    logger.exception("stage '%s' failed", stage_name)
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

                pipeline_result = ISPTSPipelineResult(
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
                    ispts_pipeline=pipeline_result,
                )

                producer.produce(
                    produce_topic, payload.model_dump_json().encode("utf-8")
                )
                journal.append(
                    action="pipeline_complete",
                    decision="success",
                    instrument=instrument_pair,
                    timeframe=timeframe,
                )
                enriched_payloads_processed_total.inc()
                processing_latency_seconds.observe(
                    time.perf_counter() - start_time
                )
            consumer.commit(msg)
    finally:
        if producer is not None:
            producer.flush()
            close = getattr(producer, "close", None)
            if callable(close):
                close()
        if consumer is not None:
            consumer.close()
        journal.flush()


if __name__ == "__main__":  # pragma: no cover - service entry point
    main()

