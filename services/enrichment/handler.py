from typing import Any, Dict
import json
import uuid

from confluent_kafka import Message
from pydantic import ValidationError

from utils.analysis_engines import build_unified_analysis
from schemas.behavioral import AnalysisPayload
from schemas import UnifiedAnalysisPayloadV1
from services.common import get_logger
from .dashboard_payload import build_harmonic_dashboard_payload

logger = get_logger(__name__)


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
        logger.error("payload validation error: %s", exc)
        ctx["consumer"].commit(msg)
        return

    tick = incoming.model_dump()
    try:
        payload: UnifiedAnalysisPayloadV1 = build_unified_analysis(tick)
        score = payload.predictive_analysis.scorer.maturity_score
        if score >= 0.85:
            data = tick.get("data", {})
            alert = {
                "strategy_name": data.get("strategy_name"),
                "symbol": payload.symbol,
                "direction": data.get("direction"),
                "entry_price": data.get("entry_price"),
                "payload_id": str(uuid.uuid4()),
            }
            ctx["redis"].publish("discord-alerts", json.dumps(alert))
        serialized = payload.model_dump_json(exclude_none=False).encode("utf-8")
        ctx["producer"].produce("enriched-analysis-payloads", value=serialized)

        # Build and emit dashboard-friendly harmonic payload
        bars = tick.get("bars") or tick.get("data", {}).get("bars", [])
        dashboard_payload = build_harmonic_dashboard_payload(payload, bars)
        serialized_dashboard = json.dumps(dashboard_payload).encode("utf-8")
        try:
            ctx["producer"].produce("harmonics", value=serialized_dashboard)
            ctx["redis"].xadd("harmonics", {"data": serialized_dashboard.decode("utf-8")})
        except Exception as emit_exc:  # pragma: no cover - non-critical emit errors
            logger.warning("failed to emit harmonic payload: %s", emit_exc)

        decision = "produced_payload"
    except Exception as e:  # pragma: no cover - log and continue
        logger.exception("analysis error: %s", e)
        decision = f"error: {e}"
    ctx["journal"].append(
        action="enrich_tick",
        decision=decision,
        instrument=ctx.get("instrument_pair"),
        timeframe=ctx.get("timeframe"),
    )
    ctx["consumer"].commit(msg)
