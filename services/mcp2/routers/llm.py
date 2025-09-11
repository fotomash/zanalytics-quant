import os
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from ..auth import verify_api_key
import yaml

router = APIRouter(dependencies=[Depends(verify_api_key)])


class WhisperRequest(BaseModel):
    question: str


class WhisperResponse(BaseModel):
    response: str


@router.post('/llm/whisperer', response_model=WhisperResponse)
async def whisperer(req: WhisperRequest) -> WhisperResponse:
    api_key = os.getenv('LLM_API_KEY')
    template = os.getenv('WHISPER_PROMPT_TEMPLATE')
    if not api_key or not template:
        raise HTTPException(status_code=503, detail='LLM not configured')

    prompt = template.format(question=req.question)
    url = os.getenv('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')

    headers = {'Authorization': f'Bearer {api_key}'}
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    content = data['choices'][0]['message']['content'].strip()
    return WhisperResponse(response=content)

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..auth import verify_api_key
from backend.mcp.schemas import StrategyPayloadV1

try:  # optional dependency; service works without it
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

router = APIRouter(prefix="/llm", dependencies=[Depends(verify_api_key)], tags=["llm"])

VERSION = "1.0"


class WhisperRequest(BaseModel):
    payload: StrategyPayloadV1
    questions: Optional[List[str]] = None
    notes: Optional[str] = None


class ResponseMeta(BaseModel):
    endpoint: str
    version: str
    stub: bool = Field(False, description="True when response is a stub due to missing OpenAI")


class WhisperResponse(BaseModel):
    signal: str
    risk: str
    action: str
    journal: str
    meta: ResponseMeta


def _build_prompt(data: WhisperRequest, nudges: bool = True) -> str:
    p = data.payload
    qs = data.questions or []
    questions = "\n".join(f"- {q}" for q in qs)
    notes = data.notes or ""
    nudge_line = (
        "\nBehavioral nudges: prefer patience/cooldown over overtrading; align with risk gates.\n"
        if nudges
        else "\n"
    )
    return f"""
You are Whisperer, a concise trading copilot. Using the payload below, respond with:
Signal • Risk • Action • Journal — four short paragraphs.{nudge_line}Payload
- Strategy: {p.strategy}
- Symbol/TF: {p.market.symbol} / {p.market.timeframe}
- Features: {p.features.indicators}
- Positions: open={p.positions.open}, closed={p.positions.closed}
- Risk cfg: max_risk={p.risk.max_risk_per_trade}
- Notes: {notes}

Operator Questions (optional):
{questions}
""".strip()


async def _suggest(body: WhisperRequest, endpoint: str, nudges: bool) -> WhisperResponse:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = _build_prompt(body, nudges=nudges)

    if not api_key or OpenAI is None:
        # Deterministic stub for offline/dev
        return WhisperResponse(
            signal="[stub] Bias modest; await higher confluence and clean structure.",
            risk="Respect cooldown; size <= max_risk; avoid news whips.",
            action="No trade yet; set alerts at key levels; review after next bar.",
            journal="Context logged; hypothesis: momentum fragile; watch liquidity sweeps.",
            meta=ResponseMeta(endpoint=endpoint, version=VERSION, stub=True),
        )

    try:
        client = OpenAI(api_key=api_key)
        msg = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": "You are Whisperer, a concise trading copilot."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = (msg.choices[0].message.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=503, detail="LLM service unavailable") from e

    # Basic parsing into four parts; tolerant to formatting
    parts = [s.strip() for s in content.replace("•", ":").splitlines() if s.strip()]

    def extract(label: str) -> str:
        for line in parts:
            if line.lower().startswith(label):
                return line.split(":", 1)[-1].strip()
        return ""

    return WhisperResponse(
        signal=extract("signal") or content,
        risk=extract("risk"),
        action=extract("action"),
        journal=extract("journal"),
        meta=ResponseMeta(endpoint=endpoint, version=VERSION),
    )


@router.post("/whisperer", response_model=WhisperResponse)
async def whisperer_suggest(body: WhisperRequest) -> WhisperResponse:
    """Return guidance with behavioral nudges."""
    return await _suggest(body, endpoint="whisperer", nudges=True)


@router.post("/simple", response_model=WhisperResponse)
async def simple_suggest(body: WhisperRequest) -> WhisperResponse:
    """Return baseline guidance without behavioral nudges."""
    return await _suggest(body, endpoint="simple", nudges=False)


class ManifestRequest(BaseModel):
    key: str
    ctx: Dict[str, Any] = Field(default_factory=dict)


class ManifestResponse(BaseModel):
    response: str
    stub: bool = False


@router.post("/run_manifest", response_model=ManifestResponse)
async def run_manifest(body: ManifestRequest) -> ManifestResponse:
    """Render a prompt from ``session_manifest.yaml`` and return the LLM response."""
    manifest_path = Path(__file__).resolve().parents[3] / "session_manifest.yaml"
    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh) or {}
    except FileNotFoundError:  # pragma: no cover - misconfiguration
        raise HTTPException(status_code=503, detail="session manifest missing")

    prompts = manifest.get("whisperer_prompts", {})
    template = prompts.get(body.key)
    if not template:
        raise HTTPException(status_code=404, detail="prompt key not found")

    try:
        prompt = template.format(**body.ctx)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing ctx key: {exc.args[0]}")

    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key or OpenAI is None:
        return ManifestResponse(response=prompt, stub=True)

    try:
        client = OpenAI(api_key=api_key)
        msg = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = (msg.choices[0].message.content or "").strip()
    except Exception as e:  # pragma: no cover - network failure
        raise HTTPException(status_code=503, detail="LLM service unavailable") from e

    return ManifestResponse(response=content)
