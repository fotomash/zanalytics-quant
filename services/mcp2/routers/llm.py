import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import verify_api_key
from backend.mcp.schemas import StrategyPayloadV1

try:  # optional dependency; service works without it
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/llm", dependencies=[Depends(verify_api_key)])


class WhisperRequest(BaseModel):
    payload: StrategyPayloadV1
    questions: Optional[List[str]] = None
    notes: Optional[str] = None


class WhisperResponse(BaseModel):
    signal: str
    risk: str
    action: str
    journal: str


def _build_prompt(data: WhisperRequest) -> str:
    p = data.payload
    qs = data.questions or []
    questions = "\n".join(f"- {q}" for q in qs)
    notes = data.notes or ""
    return f"""
You are Whisperer, a concise trading copilot. Using the payload below, respond with:
Signal • Risk • Action • Journal — four short paragraphs.

Behavioral nudges: prefer patience/cooldown over overtrading; align with risk gates.

Payload
- Strategy: {p.strategy}
- Symbol/TF: {p.market.symbol} / {p.market.timeframe}
- Features: {p.features.indicators}
- Positions: open={p.positions.open}, closed={p.positions.closed}
- Risk cfg: max_risk={p.risk.max_risk_per_trade}
- Notes: {notes}

Operator Questions (optional):
{questions}
""".strip()


@router.post("/whisper", response_model=WhisperResponse)
async def whisper_suggest(body: WhisperRequest) -> WhisperResponse:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = _build_prompt(body)

    if not api_key or OpenAI is None:
        # Deterministic stub for offline/dev
        return WhisperResponse(
            signal="Bias modest; await higher confluence and clean structure.",
            risk="Respect cooldown; size <= max_risk; avoid news whips.",
            action="No trade yet; set alerts at key levels; review after next bar.",
            journal="Context logged; hypothesis: momentum fragile; watch liquidity sweeps.",
        )

    try:
        client = OpenAI(api_key=api_key)
        msg = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Whisperer, a concise trading copilot."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = (msg.choices[0].message.content or "").strip()
    except Exception as exc:  # best-effort fallback
        content = (
            "Signal: steady. Risk: moderate. Action: wait for structure. "
            "Journal: payload recorded."
        )

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
    )

