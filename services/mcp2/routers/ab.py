from __future__ import annotations

import json
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from ..auth import verify_api_key
from ..storage import redis_client

from .echonudge import SYSTEM_PROMPT as EN_SYSTEM_PROMPT, _call_ollama  # reuse

try:  # optional dependency
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


router = APIRouter(prefix="/llm/ab", dependencies=[Depends(verify_api_key)], tags=["llm"])


class ABRequest(BaseModel):
    scenario: Optional[str] = Field(
        default=None,
        description="Named scenario to compose a concise prompt (e.g., 'winner_spring_vol').",
    )
    prompt: Optional[str] = Field(
        default=None, description="Explicit prompt; overrides scenario composition if provided."
    )
    features: dict[str, Any] = Field(default_factory=dict, description="Feature map for scenario.")
    publish_on_conflict: bool = Field(default=False, description="Publish Redis alert on conflict.")


class ABResponse(BaseModel):
    prompt: str
    echonudge: dict[str, Any]
    whisperer: dict[str, Any]
    conflict: bool
    diff: dict[str, Any]
    published: bool


def _compose_prompt(name: str, f: dict[str, Any]) -> str:
    n = (name or "").lower()
    # Winners
    if n in ("winner_spring_vol", "spring_vol"):
        phase = f.get("phase", "spring")
        vol = f.get("vol", 300)
        rr = f.get("rr", "2R")
        return f"Phase={phase} vol={vol} rr={rr}. EchoNudge: confirm strength vs trap?"
    if n in ("winner_sweep_prob", "sweep_prob"):
        p = f.get("sweep_prob", 0.72)
        side = f.get("side", "long")
        return f"sweep_prob={p} side={side}. EchoNudge: inducement risk?"
    if n in ("winner_corr_conv", "corr_conv"):
        corr = f.get("corr", 0.82)
        b1 = f.get("bias1", "long")
        b2 = f.get("bias2", "long")
        return f"corr={corr} bias1={b1} bias2={b2}. EchoNudge: conviction boost yes/no?"
    if n in ("winner_ob_bos", "ob_bos"):
        ob = f.get("ob", "valid")
        bos = f.get("bos", "up")
        htf = f.get("htf", "far")
        return f"OB={ob} BOS={bos} HTF={htf}. EchoNudge: scale entry or partial?"
    # Protectors
    if n in ("protector_dd", "dd_day"):
        dd = f.get("dd_day", "3.2%")
        return f"dd_day={dd}. EchoNudge: block all signals and cool down?"
    if n in ("protector_trade_count", "overtrade"):
        t = f.get("trades_today", 7)
        return f"trades_today={t}. EchoNudge: overtrading risk—cooldown yes/no?"
    if n in ("protector_silent", "silent_tick"):
        silence = f.get("silence", "30s")
        session = f.get("session", "high")
        return f"silence={silence} session={session}. EchoNudge: raise caution alert?"
    # Wildcards
    if n in ("ab_compare", "ab"):
        phase = f.get("phase", "neutral")
        conf = f.get("conf", 0.64)
        vol = f.get("vol", 180)
        return f"Echo vs Whisper: phase={phase} conf={conf} vol={vol}. Where disagree most?"
    # Fallback
    return f.get("prompt") or "phase=neutral conf=0.6. EchoNudge: hold or sell?"


async def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key or OpenAI is None:
        # Offline stub mirrors the contract
        return json.dumps({"label": "skip", "priority": "low", "action": "wait", "reason": "openai off"})
    client = OpenAI(api_key=api_key)
    from asyncio import to_thread

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
    def _chat() -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()

    try:
        return await to_thread(_chat)
    except Exception:
        return json.dumps(
            {
                "label": "skip",
                "priority": "low",
                "action": "wait",
                "reason": "openai error",
            }
        )


def _diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in ("label", "action", "priority"):
        if (a.get(k) or "").lower() != (b.get(k) or "").lower():
            out[k] = {"echo": a.get(k), "whisper": b.get(k)}
    return out


async def _maybe_publish(diff: dict[str, Any], prompt: str, en: dict[str, Any], wh: dict[str, Any], enabled: bool) -> bool:
    if not enabled or not diff:
        return False
    try:
        payload = {
            "event": "ab_conflict",
            "prompt": prompt,
            "diff": diff,
            "echo": en,
            "whisper": wh,
        }
        await redis_client.redis.publish("telegram-alerts", json.dumps(payload))
        AB_PUBLISHED.inc()
        return True
    except Exception:
        return False


@router.post("/echonudge_whisperer", response_model=ABResponse)
async def ab_echonudge_whisperer(body: ABRequest) -> ABResponse:
    prompt = body.prompt or _compose_prompt(body.scenario or "", body.features)

    # EchoNudge via Ollama
    AB_RUNS.labels("echonudge").inc()
    en_raw = await _call_ollama(prompt)
    try:
        en = json.loads(en_raw)
        if not isinstance(en, dict):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=502, detail="invalid EchoNudge JSON")

    # Whisperer via OpenAI (same contract/system prompt)
    AB_RUNS.labels("whisperer").inc()
    wh_raw = await _call_openai(prompt)
    try:
        wh = json.loads(wh_raw)
        if not isinstance(wh, dict):
            raise ValueError
    except Exception:
        # Normalize fallback: map free text into minimal object
        wh = {"label": "skip", "priority": "low", "action": "wait", "reason": "non-json"}

    d = _diff(en, wh)
    conflict = bool(d)
    published = await _maybe_publish(d, prompt, en, wh, body.publish_on_conflict)

    return ABResponse(prompt=prompt, echonudge=en, whisperer=wh, conflict=conflict, diff=d, published=published)


# Metrics
from prometheus_client import Counter, REGISTRY

AB_RUNS = Counter(
    "mcp2_ab_runs_total", "A/B runs per engine", ["engine"], registry=REGISTRY
)
AB_PUBLISHED = Counter(
    "mcp2_ab_conflicts_published_total", "Conflicts published to Redis", registry=REGISTRY
)
