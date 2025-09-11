from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

from backend.mcp.schemas import StrategyPayloadV1
from .routers.llm import WhisperRequest, WhisperResponse, _suggest
from .storage import redis_client
from .llm_calls import call_local_echo, call_whisperer

logger = logging.getLogger(__name__)

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "session_manifest.yaml"
try:
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        MANIFEST = yaml.safe_load(fh) or {}
except FileNotFoundError:  # pragma: no cover - deploy misconfiguration
    MANIFEST = {}
    logger.error("session manifest not found: %s", MANIFEST_PATH)

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


LOCAL_THRESHOLD = float(os.getenv("LOCAL_THRESHOLD", "0.5"))


class AnalyzeQuery(BaseModel):
    """Query for direct analysis selecting the appropriate LLM agent."""

    symbol: str


def format_whisperer_prompt(**runtime_values: object) -> str:
    """Retrieve and format the Wyckoff simulation prompt.

    Falls back to ``runtime_values['prompt']`` if the manifest does not
    contain the expected template. Missing format keys raise a clear error.
    """

    prompts = MANIFEST.get("whisperer_prompts", {})
    template = prompts.get("wyckoff_simulation")
    if not template:
        logger.error("wyckoff_simulation prompt missing in manifest")
        return str(runtime_values.get("prompt", ""))
    try:
        return template.format(**runtime_values)
    except KeyError as exc:
        missing = exc.args[0]
        raise HTTPException(status_code=500, detail=f"missing prompt value: {missing}") from exc


@app.post("/llm/analyze")
async def analyze_query(query: AnalyzeQuery) -> Dict[str, str]:
    """Route analysis to LocalEcho or Whisperer based on confidence score."""

    key = redis_client.ns(query.symbol)
    try:
        entries = await redis_client.redis_streams.xrevrange(key, count=1)
    except Exception as exc:  # pragma: no cover - redis failure
        logger.error("redis stream read failed: %s", exc)
        raise HTTPException(status_code=500, detail="redis error") from exc
    if not entries:
        raise HTTPException(status_code=404, detail="stream empty")

    _, latest = entries[0]
    prompt = latest.get("prompt", "")
    confidence = float(latest.get("confidence", 0))

    values = {"prompt": prompt, "symbol": query.symbol, "confidence": confidence}
    whisper_prompt = format_whisperer_prompt(**values)

    if confidence < LOCAL_THRESHOLD:
        verdict = await call_local_echo(prompt)
        agent = "LocalEcho"
    else:
        verdict = await call_whisperer(whisper_prompt)
        agent = "Whisperer"

    logger.info("llm.analyze agent=%s symbol=%s confidence=%s", agent, query.symbol, confidence)
    return {"verdict": verdict, "agent": agent}


__all__ = ["app"]
