import os
import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import datetime

# import your existing kernel/risk/journal
from pulse_kernel import PulseKernel  # your orchestrator

APP_NAME = "pulse-api"
app = FastAPI(title="Zanalytics Pulse API", version="1.0.0")


logger = logging.getLogger(__name__)


class PulseRuntime:
    """Singleton runtime for the Pulse kernel"""
    _kernel: Optional[PulseKernel] = None

    @classmethod
    def kernel(cls) -> PulseKernel:
        if cls._kernel is None:
            cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
            if not os.path.exists(cfg_path):
                logger.warning("Pulse config file %s not found; using defaults", cfg_path)
            cls._kernel = PulseKernel(cfg_path)
        return cls._kernel


class ScoreRequest(BaseModel):
    symbol: str = Field(..., example="EURUSD")
    tf: Optional[str] = Field("M15", description="Timeframe (optional)")
    df: Optional[Dict[str, Any]] = None


class RiskRequest(BaseModel):
    size: float = Field(..., description="Risk per trade as fraction of equity, e.g. 0.005 for 0.5%")
    score: int = Field(..., ge=0, le=100)
    meta: Optional[Dict[str, Any]] = None


class JournalCreate(BaseModel):
    kind: str = Field(..., example="mt5_trade|analysis|note")
    data: Dict[str, Any]
    ts: Optional[str] = None


@app.get("/pulse/health")
def health() -> Dict[str, Any]:
    k = PulseRuntime.kernel()
    status = k.get_status()
    return {"name": APP_NAME, "time": datetime.utcnow().isoformat(), "status": status}


@app.post("/pulse/score")
async def score(req: ScoreRequest):
    k = PulseRuntime.kernel()
    payload = {"symbol": req.symbol, "tf": req.tf, "df": req.df or {}}
    result = await k.on_frame(payload)
    return {
        "symbol": req.symbol,
        "tf": req.tf,
        "score": result.get("confidence", result.get("score", 0)),
        "grade": result.get("grade", "n/a"),
        "reasons": result.get("reasons", []),
        "decision": result.get("action", "none"),
        "raw": result,
    }


@app.post("/pulse/risk")
async def risk(req: RiskRequest):
    k = PulseRuntime.kernel()
    signal = {"score": req.score, "size": req.size, "meta": req.meta or {}}
    allowed, warnings, details = k.risk_enforcer.allow(signal)  # type: ignore
    return {"allowed": allowed, "warnings": warnings, "details": details}


@app.post("/pulse/journal")
async def journal_create(req: JournalCreate):
    k = PulseRuntime.kernel()
    entry = {
        "timestamp": req.ts or datetime.utcnow().isoformat(),
        "type": req.kind,
        "data": req.data,
    }
    await k._journal_decision(entry)
    return {"ok": True, "entry": entry}


@app.get("/pulse/journal/recent")
def journal_recent(limit: int = 25):
    k = PulseRuntime.kernel()
    import redis, json
    r = redis.Redis(**k.config["redis"])
    pattern = f"journal:{datetime.utcnow().strftime('%Y%m%d')}:*"
    keys = sorted([k.decode() for k in r.scan_iter(pattern)], reverse=True)[:limit]
    out = []
    for key in keys:
        raw = r.get(key)
        if raw:
            out.append(json.loads(raw))
    return {"items": out}
