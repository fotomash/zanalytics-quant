from datetime import datetime
from typing import Any, Dict

from confluent_kafka import Message
from pydantic import ValidationError

from utils.analysis_engines import build_unified_analysis
from schemas.behavioral import AnalysisPayload


def on_message(ctx: Dict[str, Any], msg: Message) -> None:
    """Process a single Kafka message and produce a full analysis payload.

    The enriched payload conforms to :class:`~schemas.payloads.UnifiedAnalysisPayloadV1`
    and includes both ``predictive_analysis`` and ``ispts_pipeline`` details.
    """
    try:
        incoming = AnalysisPayload.model_validate_json(
            msg.value().decode("utf-8")
        )
    except ValidationError as exc:
        print(f"payload validation error: {exc}")
        ctx["consumer"].commit(msg)
        return

    tick = incoming.model_dump()
    try:
        payload = build_unified_analysis(tick)
        ctx["producer"].produce(
            ctx["enriched_topic"], value=payload.model_dump_json().encode("utf-8")
        )
        decision = "produced_payload"
    except Exception as e:  # pragma: no cover - log and continue
        print(f"analysis error: {e}")
        decision = f"error: {e}"
    ctx["journal"].append(
        action="enrich_tick",
        decision=decision,
        instrument=ctx.get("instrument_pair"),
        timeframe=ctx.get("timeframe"),
    )
    ctx["consumer"].commit(msg)
