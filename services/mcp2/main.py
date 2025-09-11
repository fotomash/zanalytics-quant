from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import httpx
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


LOCAL_THRESHOLD = float(os.getenv("LOCAL_THRESHOLD", "0.5"))


class AnalyzeQuery(BaseModel):
    """Query for direct analysis selecting the appropriate LLM agent."""

    symbol: str


async def call_local_echo(prompt: str) -> str:
    """Send the prompt to the local Ollama instance."""

    url = os.getenv("LOCAL_ECHO_URL")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"prompt": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("verdict") or data.get("response") or str(data)
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("local echo request failed: %s", exc)
    return f"Local echo unavailable for: {prompt}"


async def call_whisperer(prompt: str) -> str:
    """Send the prompt to the cloud Whisperer service."""

    url = os.getenv("WHISPERER_URL")
    if url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={"prompt": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("verdict") or data.get("response") or str(data)
        except Exception as exc:  # pragma: no cover - network failure
            logger.error("whisperer request failed: %s", exc)
    return f"Whisperer unavailable for: {prompt}"


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

    if confidence < LOCAL_THRESHOLD:
        verdict = await call_local_echo(prompt)
        agent = "LocalEcho"
    else:
        verdict = await call_whisperer(prompt)
        agent = "Whisperer"

    logger.info("llm.analyze agent=%s symbol=%s confidence=%s", agent, query.symbol, confidence)
    return {"verdict": verdict, "agent": agent}


__all__ = ["app"]
