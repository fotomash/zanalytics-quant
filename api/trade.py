from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from trade_bridge import open_position, close_position, modify_sl_tp

router = APIRouter(prefix="/trade", tags=["trade"])


class OpenRequest(BaseModel):
    symbol: str
    side: str
    volume: float
    type: str = Field("market", pattern="^(market|limit|stop)$")
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    deviation: int = 10
    client_order_id: str | None = None


@router.post("/open")
def open_trade(req: OpenRequest):
    try:
        result = open_position(
            symbol=req.symbol,
            side=req.side,
            volume=req.volume,
            type_=req.type,
            price=req.price,
            sl=req.sl,
            tp=req.tp,
            deviation=req.deviation,
        )
        return {"result": result._asdict()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class CloseRequest(BaseModel):
    ticket: int
    volume: float | None = None
    deviation: int = 10


@router.post("/close")
def close_trade(req: CloseRequest):
    try:
        result = close_position(req.ticket, req.volume, req.deviation)
        return {"result": result._asdict()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class ModifyRequest(BaseModel):
    ticket: int
    sl: float | None = None
    tp: float | None = None


@router.post("/modify")
def modify_trade(req: ModifyRequest):
    try:
        result = modify_sl_tp(req.ticket, req.sl, req.tp)
        return {"result": result._asdict()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
