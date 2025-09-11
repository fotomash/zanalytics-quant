import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, Response, FileResponse
from pydantic import BaseModel, ValidationError
from typing import Any, Callable
import json
import asyncio
import httpx
import time
import logging
from pathlib import Path
from auth import verify_api_key

try:  # pragma: no cover - optional dependency
    import pandas as pd
except Exception:  # pragma: no cover - allow module to import without pandas
    pd = None
from dotenv import load_dotenv
from utils.time import localize_tz

try:  # pragma: no cover - optional dependency
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - allow module to import without MT5
    mt5 = None
from mt5_adapter import init_mt5
from models import (
    ACCOUNT_POSITIONS,
    SESSION_BOOT,
    TRADES_HISTORY_MT5,
    TRADES_RECENT,
    WHISPER_SUGGEST,
    ActionType,
    ActionsQuery,
)
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

init_mt5()

app = FastAPI(title="Zanalytics MCP Server")

logger = logging.getLogger(__name__)
_dotenv_candidates = [Path(__file__).parent, Path("/app"), Path.cwd()]
for base in _dotenv_candidates:
    candidate = base / ".env"
    if candidate.exists():
        load_dotenv(candidate)
        break
else:
    load_dotenv()
    logger.warning(
        "No .env file found; proceeding without loading environment variables"
    )

INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://django:8000")

REQUESTS = Counter(
    "mcp_requests_total",
    "Total MCP requests",
    ["endpoint"],
    registry=REGISTRY,
)
MCP_UP = Gauge("mcp_up", "MCP server heartbeat status", registry=REGISTRY)
MCP_TIMESTAMP = Gauge(
    "mcp_last_heartbeat_timestamp",
    "Unix timestamp of last heartbeat",
    registry=REGISTRY,
)


@app.get("/health")
async def health():
    REQUESTS.labels(endpoint="health").inc()
    try:
        return {"status": "MT5 ready", "equity": mt5.account_info().equity}
    except Exception:
        return {"status": "MT5 not ready"}


@app.get("/.well-known/openai.yaml", include_in_schema=False)
def well_known_manifest():
    REQUESTS.labels(endpoint="well_known").inc()
    return FileResponse("openai-actions.yaml", media_type="application/yaml")


async def generate_mcp_stream():
    """Generator for NDJSON streaming events."""
    MCP_UP.set(1)
    MCP_TIMESTAMP.set(time.time())
    # Send open event immediately
    yield json.dumps(
        {
            "event": "open",
            "data": {"status": "ready", "timestamp": time.time()},
        }
    ) + "\n"

    # Keep alive with heartbeat every 30 seconds
    while True:
        await asyncio.sleep(30)
        MCP_UP.set(1)
        MCP_TIMESTAMP.set(time.time())
        yield json.dumps(
            {
                "event": "heartbeat",
                "data": {"time": time.time(), "server": "mcp1.zanalytics.app"},
            }
        ) + "\n"


@app.get("/mcp")
async def mcp_stream():
    REQUESTS.labels(endpoint="mcp").inc()
    return StreamingResponse(
        generate_mcp_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.api_route(
    "/exec/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(verify_api_key)],
)
async def exec_proxy(request: Request, full_path: str):
    REQUESTS.labels(endpoint="exec").inc()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=f"{INTERNAL_API_BASE}/{full_path}",
                json=await request.json() if request.method != "GET" else None,
                headers={
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() not in ["host", "content-length"]
                },
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Internal API unreachable")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    content_type = resp.headers.get("content-type", "")
    return (
        resp.json() if content_type.startswith("application/json") else {"status": "ok"}
    )


@app.get("/metrics")
def metrics():
    REQUESTS.labels(endpoint="metrics").inc()
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


class PositionOpen(BaseModel):
    symbol: str
    side: str
    volume: float
    type: str | None = "market"
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    deviation: int | None = 10


class PositionClose(BaseModel):
    ticket: int
    volume: float | None = None
    deviation: int | None = 10


class PositionModify(BaseModel):
    ticket: int
    sl: float | None = None
    tp: float | None = None


class ExecPayload(BaseModel):
    type: str
    payload: dict


@app.post("/exec", dependencies=[Depends(verify_api_key)])
async def exec_action(payload: ExecPayload):
    """Execute trading actions via the internal API."""
    REQUESTS.labels(endpoint="exec_action").inc()
    mapping = {
        "position_open": ("/trade/open", PositionOpen),
        "position_close": ("/trade/close", PositionClose),
        "position_modify": ("/trade/modify", PositionModify),
    }

    if payload.type not in mapping:
        raise HTTPException(status_code=400, detail="Unsupported action type")

    path, model = mapping[payload.type]
    try:
        body = model(**payload.payload).dict()
    except ValidationError as exc:  # pragma: no cover - pydantic always raises HTTP 422
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{INTERNAL_API_BASE}{path}", json=body)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail="Internal API unreachable"
            ) from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/tool/search", dependencies=[Depends(verify_api_key)])
async def search_tool(query: str):
    """Search available market symbols via the internal API."""
    REQUESTS.labels(endpoint="tool_search").inc()
    if not query:
        raise HTTPException(status_code=400, detail="query required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{INTERNAL_API_BASE}/market/symbols")
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail="Internal API unreachable"
            ) from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    symbols = resp.json().get("symbols", [])
    q = query.lower()
    return {"results": [s for s in symbols if q in s.lower()]}


async def _handle_read_action(action_type: str):
    """Return stub responses matching OpenAPI schemas."""
    responses = {
        "whisper_suggest": {
            "message": "stay curious",
            "heuristics": [],
            "meta": {"user_id": "demo", "symbol": "XAUUSD"},
        },
        "session_boot": {
            "trades": [],
            "positions": [],
            "equity": None,
            "risk": None,
        },
        "trades_recent": [
            {
                "id": 1,
                "ts_open": None,
                "ts_close": None,
                "symbol": "XAUUSD",
                "side": None,
                "entry": None,
                "exit": None,
                "pnl": None,
                "rr": None,
                "strategy": None,
                "session": None,
            }
        ],
        "trades_history_mt5": [
            {
                "id": "1",
                "ts": None,
                "symbol": "XAUUSD",
                "direction": None,
                "entry": None,
                "exit": None,
                "pnl": None,
                "status": None,
            }
        ],
    }
    return responses.get(action_type, {"error": "unsupported type"})


async def _handle_account_positions():
    """Return a normalized view of open MT5 orders/positions."""
    if pd is None:  # pragma: no cover - dependency guard
        raise HTTPException(status_code=500, detail="Pandas not available")

    def normalize_mt5_orders(orders):
        df = pd.DataFrame([vars(o) for o in orders])
        if "time_setup" in df.columns:
            df["time_setup"] = pd.to_datetime(df["time_setup"], unit="s", utc=True)
            df["time_setup"] = df["time_setup"].apply(localize_tz)
        df = df[["ticket", "symbol", "type", "volume", "price_open", "time_setup"]]
        return df.rename(columns={"price_open": "entry", "type": "side"})

    if mt5 is None:  # pragma: no cover - dependency guard
        return []

    orders = mt5.orders_get(limit=10)
    if orders is None:
        return []
    df = normalize_mt5_orders(orders)
    return df.to_dict("records")


@app.post("/api/v1/actions/query", dependencies=[Depends(verify_api_key)])
async def post_actions_query(payload: ActionsQuery):
    REQUESTS.labels(endpoint="actions_query").inc()
    handlers: dict[ActionType, Callable[[], Any]] = {
        WHISPER_SUGGEST: lambda: _handle_read_action(WHISPER_SUGGEST),
        SESSION_BOOT: lambda: _handle_read_action(SESSION_BOOT),
        TRADES_RECENT: lambda: _handle_read_action(TRADES_RECENT),
        TRADES_HISTORY_MT5: lambda: _handle_read_action(TRADES_HISTORY_MT5),
        ACCOUNT_POSITIONS: _handle_account_positions,
    }

    try:
        handler = handlers[payload.type]
    except KeyError as exc:  # pragma: no cover - should be prevented by validation
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported action type: {payload.type}",
        ) from exc

    return await handler()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
