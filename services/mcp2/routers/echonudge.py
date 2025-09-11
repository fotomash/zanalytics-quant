from __future__ import annotations

import json
import os
from typing import Any, Optional

from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..storage import redis_client


router = APIRouter(prefix="/llm", dependencies=[Depends(verify_api_key)], tags=["llm"])


class EchoNudgeRequest(BaseModel):
    prompt: str = Field(..., description="Compact user prompt for EchoNudge.")
    meta: Optional[dict[str, Any]] = Field(
        default=None, description="Optional metadata/features (e.g., ctm values)."
    )


class EchoNudgeResponse(BaseModel):
    result: dict[str, Any] = Field(..., description="Parsed JSON response from model")
    raw: str = Field(..., description="Raw text returned by model (JSON string)")
    published: bool = Field(..., description="Whether an alert was published to Redis pubsub")


SYSTEM_PROMPT = (
    'You are EchoNudge, a latency-optimized labeler for market micro-events. '
    'Output only compact JSON: {"label": "...", "priority": "...", "action": "...", "reason": "..."}. '
    'Use enums: label=[hold,buy,sell,hedge,alert,ignore,exit,scale,pause,yes,no,low,med,high,skip]; '
    'priority=[low,med,high]; action=[none,alert,place,reduce,hedge,wait,scale_in,scale_out,exit_partial]. '
    'Be decisive and brief. If uncertain, label "skip" with action "wait". No extra text.'
)


@lru_cache(maxsize=None)
def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://ollama:11434")


@lru_cache(maxsize=None)
def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4")


@lru_cache(maxsize=None)
def _ollama_options() -> dict[str, Any]:
    # CPU-friendly defaults
    return {
        "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "256")),
        "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "24")),
        "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        "top_k": int(os.getenv("OLLAMA_TOP_K", "20")),
        "top_p": float(os.getenv("OLLAMA_TOP_P", "0.8")),
        "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.05")),
    }


async def _call_ollama(prompt: str) -> str:
    url = f"{_ollama_url().rstrip('/')}/api/generate"
    payload = {
        "model": _ollama_model(),
        "prompt": f"System:\n{SYSTEM_PROMPT}\n\nUser:\n{prompt}",
        "stream": False,
        "format": "json",
        "options": _ollama_options(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return str(data.get("response", "")).strip()
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - offline fallback
        # Fallback deterministic stub
        return json.dumps(
            {
                "label": "skip",
                "priority": "low",
                "action": "wait",
                "reason": "offline stub",
            }
        )


async def _maybe_publish_alert(result: dict[str, Any], prompt: str, meta: Optional[dict[str, Any]]) -> bool:
    try:
        label = str(result.get("label") or "").lower()
        action = str(result.get("action") or "").lower()
        if label == "alert" or action == "hedge":
            payload = {
                "event": "echo_nudge",
                "label": label,
                "action": action,
                "priority": result.get("priority"),
                "reason": result.get("reason"),
                "prompt": prompt,
                "meta": meta or {},
            }
            # Publish to the same pubsub channel used by pulse bot
            await redis_client.redis.publish("telegram-alerts", json.dumps(payload))
            return True
    except Exception:
        return False
    return False


@router.post("/echonudge", response_model=EchoNudgeResponse)
async def echonudge(req: EchoNudgeRequest) -> EchoNudgeResponse:
    raw = await _call_ollama(req.prompt)
    # Ensure JSON parse safety
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("model did not return object")
    except Exception:
        raise HTTPException(status_code=502, detail="invalid model JSON")

    published = await _maybe_publish_alert(result, req.prompt, req.meta)
    return EchoNudgeResponse(result=result, raw=raw, published=published)

