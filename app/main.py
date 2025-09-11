import os
import json
import time
import uvicorn
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Body, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, conlist, confloat
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
from api.trade import router as trade_router

try:
    from pulse_kernel import PulseKernel
except Exception as e:
    raise RuntimeError(f"PulseKernel import failed: {e}")

logger = logging.getLogger("pulse-api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "pulse_api_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "pulse_api_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


class Frame(BaseModel):
    symbol: str = Field(..., examples=["EURUSD", "XAUUSD"])
    ts: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    df: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class ScoreResponse(BaseModel):
    score: confloat(ge=0, le=100)
    grade: str
    components: Dict[str, float]
    reasons: List[str]
    details: Dict[str, Any] = {}


class RiskCheckRequest(BaseModel):
    symbol: str
    intended_risk_fraction: confloat(ge=0, le=0.05) = 0.0
    confluence_score: confloat(ge=0, le=100)
    size_splits: int = 1


class RiskCheckResponse(BaseModel):
    allowed: bool
    warnings: List[str]
    details: Dict[str, Any]


class JournalEntry(BaseModel):
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    type: str = Field(..., examples=["mt5_trade", "analysis", "note"])
    data: Dict[str, Any]


class JournalAppendResponse(BaseModel):
    ok: bool
    stored: int
    last_key: str


class JournalRecentResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int


class TopSignal(BaseModel):
    symbol: str
    score: confloat(ge=0, le=100)
    bias: Optional[str] = None
    risk: Optional[str] = None
    reasons: Optional[List[str]] = None


class TopSignalsResponse(BaseModel):
    items: conlist(TopSignal, min_length=0, max_length=25)


    class PulseRuntime:
        _instance = None

        def __init__(self):
            cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
            if not os.path.exists(cfg_path):
                logger.warning("Pulse config file %s not found; using defaults", cfg_path)
            self.kernel = PulseKernel(config_path=cfg_path)
            logger.info("PulseRuntime initialized")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = PulseRuntime()
        return cls._instance


def get_runtime() -> PulseRuntime:
    return PulseRuntime.instance()


app = FastAPI(
    title="Zanalytics Pulse API",
    version=os.getenv("PULSE_API_VERSION", "1.0.0"),
    docs_url="/pulse/docs",
    redoc_url="/pulse/redoc",
    openapi_url="/pulse/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("PULSE_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trade_router)


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(latency)
    return response


@app.get("/pulse/health")
def health(rt: PulseRuntime = Depends(get_runtime)):
    return {
        "ok": True,
        "system": "Zanalytics Pulse",
        "status": rt.kernel.get_status(),
        "time": datetime.utcnow().isoformat()
    }


@app.post("/pulse/score", response_model=ScoreResponse)
async def score(frame: Frame, rt: PulseRuntime = Depends(get_runtime)):
    result = await rt.kernel._calculate_confluence(frame.dict())
    if not result or "score" not in result:
        raise HTTPException(status_code=422, detail="Scoring failed")
    return ScoreResponse(**result)


@app.post("/pulse/risk", response_model=RiskCheckResponse)
async def risk_check(payload: RiskCheckRequest, rt: PulseRuntime = Depends(get_runtime)):
    signal = {
        "symbol": payload.symbol,
        "score": payload.confluence_score,
        "size": float(payload.intended_risk_fraction),
        "splits": int(payload.size_splits),
    }
    risk = await rt.kernel._enforce_risk({"score": payload.confluence_score})
    out = {
        "allowed": risk.get("allowed", False),
        "warnings": risk.get("warnings", []),
        "details": {
            "remaining_trades": risk.get("remaining_trades"),
            "remaining_risk": risk.get("remaining_risk"),
            "cooling_active": risk.get("cooling_active", False),
            "behavioral": rt.kernel._check_behavioral_state(),
        }
    }
    return RiskCheckResponse(**out)


@app.post("/pulse/journal", response_model=JournalAppendResponse)
async def journal_append(entry: JournalEntry, rt: PulseRuntime = Depends(get_runtime)):
    decision = {
        "timestamp": entry.timestamp,
        "type": entry.type,
        "data": entry.data,
    }
    await rt.kernel._journal_decision(decision)
    last_key = f"journal:{datetime.utcnow().strftime('%Y%m%d')}:{entry.timestamp}"
    return JournalAppendResponse(ok=True, stored=1, last_key=last_key)


@app.get("/pulse/journal/recent", response_model=JournalRecentResponse)
def journal_recent(limit: int = Query(25, ge=1, le=200), rt: PulseRuntime = Depends(get_runtime)):
    r = rt.kernel.redis_client
    today_prefix = f"journal:{datetime.utcnow().strftime('%Y%m%d')}:"
    keys = sorted([k.decode() for k in r.keys(f"{today_prefix}*")])[-limit:]
    items = []
    for k in keys:
        raw = r.get(k)
        if raw:
            try:
                items.append(json.loads(raw))
            except Exception:
                logger.warning("Malformed journal item at %s", k)
    return JournalRecentResponse(items=items, total=len(items))


@app.get("/pulse/signals/top", response_model=TopSignalsResponse)
async def top_signals(symbols: Optional[str] = Query(default=None), rt: PulseRuntime = Depends(get_runtime)):
    syms = [s.strip() for s in (symbols.split(",") if symbols else ["EURUSD", "GBPUSD", "XAUUSD"])]
    scored: List[TopSignal] = []
    for s in syms:
        frame = Frame(symbol=s).dict()
        result = await rt.kernel._calculate_confluence(frame)
        if result and "score" in result:
            scored.append(TopSignal(
                symbol=s,
                score=result["score"],
                bias="BULL" if result["score"] >= 70 else "NEUTRAL",
                risk="LOW" if result["score"] >= 80 else "MEDIUM",
                reasons=result.get("reasons", [])[:3]
            ))
    scored.sort(key=lambda x: x.score, reverse=True)
    return TopSignalsResponse(items=scored[: min(10, len(scored))])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=bool(int(os.getenv("RELOAD", "0")))
    )
