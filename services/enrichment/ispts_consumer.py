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
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

import yaml
from confluent_kafka import Consumer, Producer, KafkaError

from core.session_journal import SessionJournal

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


def _load_manifest() -> Dict[str, Any]:
    return yaml.safe_load(SESSION_MANIFEST.read_text(encoding="utf-8"))


def _load_pipeline() -> List[str]:
    data = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
    return data.get("stages", [])


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
    manifest = _load_manifest()
    stages = _load_pipeline()

    topics = manifest.get("topics", {})
    consume_topics = topics.get("consume", ["raw-market-data"])
    produce_topic = topics.get("produce", "enriched-analysis-payloads")
    instrument_pair = manifest.get("instrument_pair")
    timeframe = manifest.get("timeframe")

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


if __name__ == "__main__":  # pragma: no cover - service entry point
    main()
