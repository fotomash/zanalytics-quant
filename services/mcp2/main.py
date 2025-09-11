from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml

from backend.mcp.schemas import StrategyPayloadV1
from .routers.llm import (
    WhisperRequest as SuggestRequest,
    WhisperResponse as SuggestResponse,
    _suggest,
)
from .storage import redis_client

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


@app.post("/llm/{model}/analyze", response_model=SuggestResponse)
async def analyze(model: str, body: StreamRequest) -> SuggestResponse:
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
    req = SuggestRequest(payload=payload, questions=body.questions, notes=body.notes)
    nudges = model.lower() != "simple"
    return await _suggest(req, endpoint=f"{model}/analyze", nudges=nudges)


LOCAL_THRESHOLD = float(os.getenv("LOCAL_THRESHOLD", "0.5"))


class WhisperRequest(BaseModel):
    prompt: str


class WhisperResponse(BaseModel):
    response: str
    agent: str
    whisperer: Optional[str] = None


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
        handover = False
    else:
        verdict = await call_whisperer(whisper_prompt)
        agent = "Whisperer"
        handover = True

    logger.info(
        "llm.analyze",
        extra={
            "agent": agent,
            "handover": handover,
            "symbol": query.symbol,
            "confidence": confidence,
        },
    )
    return {"verdict": verdict, "agent": agent}


@app.post("/llm/echonudge", response_model=WhisperResponse)
async def echonudge(req: WhisperRequest) -> WhisperResponse:
    """Evaluate ``prompt`` with the local Echo service.

    If the local verdict contains ``high risk`` the prompt is escalated to the
    Whisperer service for deeper analysis.
    """

    local = await call_local_echo(req.prompt)
    if "high risk" in local.lower():
        whisper = await call_whisperer(f"Escalate: {req.prompt}")
        return WhisperResponse(
            response=local, whisperer=whisper, agent="EchoNudge → Whisperer"
        )
    return WhisperResponse(response=local, agent="EchoNudge")


@app.post("/llm/whisperer", response_model=WhisperResponse)
async def whisperer(req: WhisperRequest) -> WhisperResponse:
    """Return the cloud Whisperer analysis for ``prompt``."""

    verdict = await call_whisperer(req.prompt)
    return WhisperResponse(response=verdict, agent="Whisperer")


__all__ = ["app"]
