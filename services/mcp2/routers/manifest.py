from __future__ import annotations

import json
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from session_manifest import load_prompt
from .echonudge import _call_ollama
from .ab import _call_openai
from prometheus_client import Counter, REGISTRY


router = APIRouter(prefix="/llm/manifest", dependencies=[Depends(verify_api_key)], tags=["llm"])


class RunManifestRequest(BaseModel):
    key: str = Field(..., description="Manifest prompt key to run")
    ctx: dict[str, Any] = Field(default_factory=dict, description="Context variables for formatting the template")
    engine: Literal["echonudge", "whisperer"] = Field(
        default="echonudge", description="Select local (Ollama) or cloud (OpenAI) engine"
    )


class RunManifestResponse(BaseModel):
    key: str
    engine: str
    prompt: str
    parsed: dict[str, Any]
    raw: str


@router.post("/run", response_model=RunManifestResponse)
async def run_manifest(body: RunManifestRequest) -> RunManifestResponse:
    try:
        template = load_prompt(body.key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        prompt = template.format(**body.ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"format error: {exc}")

    MANIFEST_RUNS.labels(body.key, body.engine).inc()
    if body.engine == "echonudge":
        raw = await _call_ollama(prompt)
    else:
        raw = await _call_openai(prompt)

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("expected object")
    except Exception:
        MANIFEST_JSON_FAIL.labels(body.engine).inc()
        raise HTTPException(status_code=502, detail="invalid model JSON")

    return RunManifestResponse(key=body.key, engine=body.engine, prompt=prompt, parsed=parsed, raw=raw)


# Metrics
MANIFEST_RUNS = Counter(
    "mcp2_manifest_runs_total", "Manifest prompt runs", ["key", "engine"], registry=REGISTRY
)
MANIFEST_JSON_FAIL = Counter(
    "mcp2_manifest_json_failures_total", "Manifest model JSON parse failures", ["engine"], registry=REGISTRY
)
