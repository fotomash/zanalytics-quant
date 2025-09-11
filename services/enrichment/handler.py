import json
from typing import Any, Dict

from confluent_kafka import Message

from utils.analysis_engines import build_unified_analysis


def on_message(ctx: Dict[str, Any], msg: Message) -> None:
    """Process a single Kafka message and produce enriched payload."""
    tick = json.loads(msg.value().decode("utf-8"))
    try:
        payload = build_unified_analysis(tick)
        ctx["producer"].produce(ctx["enriched_topic"], value=payload.model_dump_json())
    except Exception as e:  # pragma: no cover - log and continue
        print(f"analysis error: {e}")
    ctx["consumer"].commit(msg)
