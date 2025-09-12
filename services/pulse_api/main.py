import os
import logging
import time
from typing import Any, Dict, Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from datetime import datetime
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

# import your existing kernel/risk/journal
from pulse_kernel import PulseKernel  # your orchestrator

APP_NAME = "pulse-api"
app = FastAPI(title="Zanalytics Pulse API", version="1.0.0")


logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "pulse_request_latency_seconds", "Request latency", ["endpoint", "method"]
)
REQUEST_ERRORS = Counter(
    "pulse_request_errors_total", "Total request errors", ["endpoint", "exception"]
)
SCORE_EVALS = Counter(
    "pulse_score_evaluations_total", "Total score evaluations"
)
RISK_EVALS = Counter(
    "pulse_risk_evaluations_total", "Total risk evaluations"
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    endpoint = request.url.path
    method = request.method
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        REQUEST_ERRORS.labels(endpoint=endpoint, exception=exc.__class__.__name__).inc()
        raise
    finally:
        duration = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Simple API key authentication
API_KEY_HEADER = "X-API-Key"
EXPECTED_API_KEY = os.getenv("PULSE_API_KEY")


def require_api_key(api_key: str = Header(..., alias=API_KEY_HEADER)) -> str:
    """Validate the provided API key against ``PULSE_API_KEY``.

    Raises ``HTTPException`` if the key is missing or invalid. The environment
    variable must be set; otherwise a 500 error is returned.
    """
    if not EXPECTED_API_KEY:
        logger.error("PULSE_API_KEY not set; refusing all requests")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured",
        )
    if api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return api_key


class PulseRuntime:
    """Singleton runtime for the Pulse kernel.

    The configuration path is taken from the ``PULSE_CONFIG`` environment
    variable or defaults to ``pulse_config.yaml``. Callers should ensure the
    path points to a valid YAML file.
    """

    _kernel: Optional[PulseKernel] = None

    @classmethod
    def kernel(cls) -> PulseKernel:
        if cls._kernel is None:
            cfg_path = os.getenv("PULSE_CONFIG", "pulse_config.yaml")
            if not os.path.exists(cfg_path):
                logger.warning("Pulse config file %s not found; using defaults", cfg_path)
            else:
                logger.info("Using Pulse config %s", cfg_path)
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
async def score(req: ScoreRequest, api_key: str = Depends(require_api_key)):
    k = PulseRuntime.kernel()
    payload = {"symbol": req.symbol, "tf": req.tf, "df": req.df or {}}
    result = await k.on_frame(payload)
    SCORE_EVALS.inc()
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
async def risk(req: RiskRequest, api_key: str = Depends(require_api_key)):
    k = PulseRuntime.kernel()
    signal = {"score": req.score, "size": req.size, "meta": req.meta or {}}
    allowed, warnings, details = k.risk_enforcer.allow(signal)  # type: ignore
    RISK_EVALS.inc()
    return {"allowed": allowed, "warnings": warnings, "details": details}


@app.post("/pulse/journal")
async def journal_create(req: JournalCreate, api_key: str = Depends(require_api_key)):
    k = PulseRuntime.kernel()
    entry = {
        "timestamp": req.ts or datetime.utcnow().isoformat(),
        "type": req.kind,
        "data": req.data,
    }
    await k._journal_decision(entry)
    return {"ok": True, "entry": entry}


@app.get("/pulse/journal/recent")
def journal_recent(limit: int = 25, api_key: str = Depends(require_api_key)):
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


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Release resources on application shutdown."""
    k = PulseRuntime.kernel()
    k.flush_and_close()
