import os
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
