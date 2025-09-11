from datetime import datetime
import json
import yaml
import pathlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from core.predictive_scorer import PredictiveScorer

router = APIRouter(prefix="/api/pulse", tags=["pulse"])

conf_dir = pathlib.Path(__file__).parent.parent / "knowledge" / "strategies"
conf_cfg = yaml.safe_load((conf_dir / "hybrid_confluence.yaml").read_text())
_smc_cfg = json.loads((conf_dir / "smc_advanced.json").read_text())
_wyckoff_cfg = json.loads((conf_dir / "wyckoff_basic.json").read_text())
scorer = PredictiveScorer(config_path=str(conf_dir / "hybrid_confluence.yaml"))


class BarIn(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


@router.post("/score")
async def receive_bar(bar: BarIn):
    """Compute confluence score for an aggregated bar."""
    try:
        result = scorer.score(bar.dict())
        return {
            "symbol": bar.symbol,
            "maturity_score": result.get("maturity_score", 0),
            "grade": result.get("grade"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:  # pragma: no cover - simple passthrough
        raise HTTPException(status_code=500, detail=str(exc))
