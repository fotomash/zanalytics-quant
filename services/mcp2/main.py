from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.mcp.schemas import StrategyPayloadV1
from .routers.llm import WhisperRequest, WhisperResponse, _suggest
from .storage import redis_client

logger = logging.getLogger(__name__)

app = FastAPI()


class StreamRequest(BaseModel):
    """Request model for analyzing the latest payload from a Redis stream."""

    stream: str
    last_id: str = "-"
    questions: Optional[List[str]] = None
    notes: Optional[str] = None


@app.post("/llm/{model}/analyze", response_model=WhisperResponse)
async def analyze(model: str, body: StreamRequest) -> WhisperResponse:
    """Read the most recent payload from ``body.stream`` and analyze it.

    The endpoint looks up the latest entry in the named Redis stream, parses the
    ``StrategyPayloadV1`` payload, and passes it to the existing LLM suggestion
    helper. The response includes the prompt version metadata from the helper.
    """

    key = redis_client.ns(body.stream)
    try:
        entries = await redis_client.redis_streams.xrevrange(key, count=1)
    except Exception as exc:  # pragma: no cover - redis failure
        logger.error("redis stream read failed: %s", exc)
        raise HTTPException(status_code=500, detail="redis error") from exc

    if not entries:
        raise HTTPException(status_code=404, detail="stream empty")

    _, fields = entries[0]
    payload_json = fields.get("payload")
    if not payload_json:
        raise HTTPException(status_code=400, detail="missing payload field")

    payload = StrategyPayloadV1.model_validate_json(payload_json)
    req = WhisperRequest(payload=payload, questions=body.questions, notes=body.notes)
    nudges = model.lower() != "simple"
    return await _suggest(req, endpoint=f"{model}/analyze", nudges=nudges)


__all__ = ["app"]
