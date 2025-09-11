from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
import math
import os
import threading
import time
import json
from prometheus_client import Counter, Gauge, REGISTRY, generate_latest
from schemas.health import HealthStatus

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - no redis available
    redis = None  # type: ignore

from alerts.telegram_alerts import _send as _send_telegram  # type: ignore

try:
    import MetaTrader5 as mt5
except Exception as e:
    # Defer raising until startup so container can boot
    mt5 = None
    _mt5_import_error = e
else:
    _mt5_import_error = None

app = FastAPI(title="MT5 Gateway", version="1.0.0")

# Prometheus metrics
raw_messages_published_total = Counter(
    "raw_messages_published_total",
    "Total raw messages published",
)
mt5_connection = Gauge("mt5_connection", "MT5 connection status (1=ok,0=down)")


HEARTBEAT_CHANNEL = os.getenv("MT5_HEARTBEAT_CHANNEL", "monitoring:mt5")
HEARTBEAT_INTERVAL = float(os.getenv("MT5_HEARTBEAT_INTERVAL", "30"))
ALERT_THRESHOLD = float(os.getenv("MT5_HEARTBEAT_ALERT_THRESHOLD", "90"))

_last_heartbeat = time.time()


def _heartbeat_publisher() -> None:
    """Publish periodic heartbeats to Redis."""
    global _last_heartbeat
    if not redis:
        return
    try:
        rds = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    except Exception:
        return
    while True:
        payload = json.dumps({"ts": time.time()})
        try:
            rds.publish(HEARTBEAT_CHANNEL, payload)
            _last_heartbeat = time.time()
        except Exception:
            pass
        time.sleep(HEARTBEAT_INTERVAL)


def _heartbeat_watchdog() -> None:
    """Trigger alert if heartbeat publishing stops."""
    alerted = False
    while True:
        elapsed = time.time() - _last_heartbeat
        if elapsed > ALERT_THRESHOLD and not alerted:
            try:
                _send_telegram(
                    f"⚠️ MT5 heartbeat missing for {int(elapsed)}s"
                )
            except Exception:
                pass
            alerted = True
        elif elapsed <= ALERT_THRESHOLD:
            alerted = False
        time.sleep(max(HEARTBEAT_INTERVAL, ALERT_THRESHOLD / 2))


@app.on_event("startup")
def startup():
    if _mt5_import_error is not None:
        raise RuntimeError(f"Failed to import MetaTrader5: {_mt5_import_error}")
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize() failed: {mt5.last_error()}")
    # Attempt login if env credentials are provided
    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")
    if login and password and server:
        try:
            mt5.login(login=int(login), password=password, server=server)
        except Exception:
            # Non-fatal; endpoints will surface failures
            pass
    global _last_heartbeat
    _last_heartbeat = time.time()
    threading.Thread(target=_heartbeat_publisher, daemon=True).start()
    threading.Thread(target=_heartbeat_watchdog, daemon=True).start()


@app.on_event("shutdown")
def shutdown():
    try:
        mt5.shutdown()
    except Exception:
        pass


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    connected = mt5.initialize() if mt5 else False
    mt5_connection.set(1 if connected else 0)
    return HealthStatus.healthy("mt5-gateway", {"mt5": connected})


@app.get("/metrics")
def metrics() -> Response:
    return PlainTextResponse(generate_latest(REGISTRY))


@app.get("/routes")
def routes():
    # quick visibility of available endpoints
    return sorted([getattr(r, "path", str(r)) for r in app.router.routes])


@app.get("/account_info")
def account_info():
    info = mt5.account_info()
    if info is None:
        raise HTTPException(status_code=502, detail="mt5_account_info_none")
    try:
        return info._asdict()
    except Exception:
        # Fallback: jsonify attributes
        return {k: getattr(info, k) for k in dir(info) if not k.startswith("_")}


@app.get("/positions_get")
def positions_get():
    pos = mt5.positions_get()
    if not pos:
        return []
    out: List[Dict[str, Any]] = []
    for p in pos:
        try:
            out.append(p._asdict())
        except Exception:
            out.append(
                {
                    "ticket": int(getattr(p, "ticket", 0)),
                    "symbol": getattr(p, "symbol", ""),
                    "type": int(getattr(p, "type", -1)),
                    "volume": float(getattr(p, "volume", 0.0)),
                    "price_open": float(getattr(p, "price_open", 0.0)),
                    "price_current": float(getattr(p, "price_current", 0.0)),
                    "profit": float(getattr(p, "profit", 0.0)),
                    "sl": float(getattr(p, "sl", 0.0)),
                    "tp": float(getattr(p, "tp", 0.0)),
                }
            )
    return out


def _find_pos(ticket: int):
    pos = mt5.positions_get()
    if not pos:
        return None
    for p in pos:
        if int(p.ticket) == int(ticket):
            return p
    return None


def _round_step(value: float, step: float) -> float:
    if not step or step <= 0:
        return value
    # floor to step with numeric stability
    return math.floor((value + 1e-12) / step) * step


def _clamp_volume(symbol: str, requested: float) -> float:
    si = mt5.symbol_info(symbol)
    vol_min = getattr(si, "volume_min", 0.01) if si else 0.01
    vol_max = getattr(si, "volume_max", requested) if si else requested
    vol_step = getattr(si, "volume_step", 0.01) if si else 0.01
    v = max(min(requested, float(vol_max)), float(vol_min))
    v = _round_step(v, float(vol_step))
    # Don't return zero or negative
    if v <= 0:
        v = float(vol_min)
    return round(v, 3)


def _opposite_side(position_type: int) -> int:
    # POSITION_TYPE_BUY = 0, POSITION_TYPE_SELL = 1
    # ORDER_TYPE_BUY / ORDER_TYPE_SELL
    return mt5.ORDER_TYPE_BUY if position_type == mt5.POSITION_TYPE_SELL else mt5.ORDER_TYPE_SELL


def _deal(symbol: str, volume: float, side: int, deviation: int = 20, comment: str = "", position: Optional[int] = None) -> Dict[str, Any]:
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        raise HTTPException(502, detail="no_tick")
    price = tick.ask if side == mt5.ORDER_TYPE_BUY else tick.bid
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": side,
        "price": float(price),
        "deviation": int(deviation),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "comment": comment or "",
    }
    if position is not None:
        req["position"] = int(position)
    res = mt5.order_send(req)
    try:
        return res._asdict()
    except Exception:
        return {"retcode": getattr(res, "retcode", None)}


class PartialCloseV2(BaseModel):
    ticket: int
    fraction: Optional[float] = None
    volume: Optional[float] = None
    deviation: Optional[int] = 20
    comment: Optional[str] = None


@app.post("/partial_close_v2")
def partial_close_v2(body: PartialCloseV2):
    pos = _find_pos(body.ticket)
    if not pos:
        raise HTTPException(404, detail="position_not_found")
    symbol = pos.symbol
    full = float(pos.volume)
    if body.volume is not None:
        vol_req = float(body.volume)
    else:
        frac = float(body.fraction or 1.0)
        vol_req = full * frac

    vol = _clamp_volume(symbol, max(min(vol_req, full), 0.0))
    if vol <= 0:
        raise HTTPException(400, detail="volume_non_positive")

    side = _opposite_side(int(pos.type))
    result = _deal(symbol, vol, side, deviation=int(body.deviation or 20),
                   comment=body.comment or f"partial_close_v2 ticket {body.ticket}",
                   position=body.ticket)
    return {"ok": True, "result": result}


class PartialCloseLegacy(BaseModel):
    ticket: int
    symbol: str
    fraction: Optional[float] = None
    volume: Optional[float] = None
    deviation: Optional[int] = 20
    comment: Optional[str] = None


@app.post("/partial_close")
def partial_close(body: PartialCloseLegacy):
    pos = _find_pos(body.ticket)
    if not pos:
        raise HTTPException(404, detail="position_not_found")
    full = float(pos.volume)
    if body.volume is not None:
        vol_req = float(body.volume)
    else:
        frac = float(body.fraction or 1.0)
        vol_req = full * frac

    vol = _clamp_volume(body.symbol, max(min(vol_req, full), 0.0))
    side = _opposite_side(int(pos.type))
    result = _deal(body.symbol, vol, side, deviation=int(body.deviation or 20),
                   comment=body.comment or f"partial_close ticket {body.ticket}",
                   position=body.ticket)
    return {"ok": True, "result": result}


class ClosePayload(BaseModel):
    ticket: int
    deviation: Optional[int] = 20
    comment: Optional[str] = None


@app.post("/close_position")
def close_position(body: ClosePayload):
    pos = _find_pos(body.ticket)
    if not pos:
        raise HTTPException(404, detail="position_not_found")
    symbol = pos.symbol
    vol = float(pos.volume)
    side = _opposite_side(int(pos.type))
    result = _deal(symbol, vol, side, deviation=int(body.deviation or 20),
                   comment=body.comment or f"close_position ticket {body.ticket}",
                   position=body.ticket)
    return {"ok": True, "result": result}


class MarketOrder(BaseModel):
    symbol: str
    volume: float
    type: str  # "BUY" or "SELL"
    deviation: Optional[int] = 20
    type_filling: Optional[str] = "ORDER_FILLING_IOC"
    comment: Optional[str] = None


@app.post("/send_market_order")
def send_market_order(body: MarketOrder):
    side = mt5.ORDER_TYPE_BUY if body.type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    vol = _clamp_volume(body.symbol, float(body.volume))
    result = _deal(body.symbol, vol, side, deviation=int(body.deviation or 20), comment=body.comment or "")
    return {"ok": True, "result": result}
