from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Import runtime / kernel layer
from pulse_kernel import PulseKernel

app = FastAPI(title="Zanalytics Pulse API", version="1.0.0", docs_url="/")
security = HTTPBearer()

# rate limit per token (60 requests per minute)

def token_identifier(request: Request) -> str:
    """Use bearer token for rate limiting."""
    return request.headers.get("Authorization", "")

limiter = Limiter(key_func=token_identifier)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- AUTH (simple Bearer) ---
API_TOKENS: set[str] = set()  # fill from env/secret store on startup

def auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    token = credentials.credentials
    if token not in API_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return True

# --- Models ---

class ScoreRequest(BaseModel):
    symbol: str = Field(..., examples=["EURUSD"])
    timeframe: str = Field("M5", examples=["M1", "M5", "M15", "H1"])
    frame: Optional[Dict[str, Any]] = None  # optionally raw frame or ts window


class ScoreResponse(BaseModel):
    timestamp: datetime
    symbol: str
    score: float
    grade: str
    reasons: List[str]
    components: Dict[str, float]


class RiskRequest(BaseModel):
    symbol: str
    intended_risk: float = Field(
        ..., description="Fraction of account, e.g. 0.005 for 0.5%"
    )
    size: Optional[float] = Field(
        None, description="Position size fraction if already chosen"
    )


class RiskResponse(BaseModel):
    allowed: bool
    warnings: List[str]
    details: Dict[str, Any]


class JournalEntry(BaseModel):
    type: str  # "pre_trade" | "post_trade" | "note"
    data: Dict[str, Any]


# --- Runtime singleton (Kernel under the hood) ---
KERNEL = PulseKernel()  # or PulseRuntime().kernel


# --- Health ---
@app.get("/pulse/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "kernel": KERNEL.get_status()}


# --- Score ---
@app.post(
    "/pulse/score",
    response_model=ScoreResponse,
    dependencies=[Depends(auth)],
)
@limiter.limit("60/minute")
def score(req: ScoreRequest) -> ScoreResponse:
    data = req.frame or {"symbol": req.symbol, "timeframe": req.timeframe}
    result = KERNEL.confluence_scorer.score({"df": data})
    return ScoreResponse(
        timestamp=datetime.utcnow(),
        symbol=req.symbol,
        score=result["score"],
        grade=result["grade"],
        reasons=result.get("reasons", []),
        components=result.get("components", {}),
    )


# --- Risk ---
@app.post(
    "/pulse/risk",
    response_model=RiskResponse,
    dependencies=[Depends(auth)],
)
@limiter.limit("60/minute")
def risk(req: RiskRequest) -> RiskResponse:
    allowed, warnings, details = KERNEL.risk_enforcer.allow(
        {"symbol": req.symbol, "size": req.size or req.intended_risk}
    )
    return RiskResponse(allowed=allowed, warnings=warnings, details=details)


# --- Journal ---
@app.post("/pulse/journal", dependencies=[Depends(auth)])
@limiter.limit("60/minute")
def journal(entry: JournalEntry) -> Dict[str, bool]:
    KERNEL.journal.write(entry.type, entry.data)
    return {"ok": True}


# --- Startup to load tokens ---
@app.on_event("startup")
def load_tokens() -> None:
    import os

    raw = os.getenv("PULSE_API_TOKENS", "")
    for t in raw.split(","):
        t = t.strip()
        if t:
            API_TOKENS.add(t)
