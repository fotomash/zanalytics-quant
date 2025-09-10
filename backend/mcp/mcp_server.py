from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, Response, JSONResponse, FileResponse
from pydantic import BaseModel
import json
import asyncio
import httpx
import os
import time
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = FastAPI(title="Zanalytics MCP Server")

INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://django:8000")

# API key expected in incoming requests; empty string by default
API_KEY = os.environ.get("MCP_API_KEY", "")

REQUESTS = Counter("mcp_requests_total", "Total MCP requests", ["endpoint"])
MCP_UP = Gauge("mcp_up", "MCP server heartbeat status")
MCP_TIMESTAMP = Gauge(
    "mcp_last_heartbeat_timestamp", "Unix timestamp of last heartbeat"
)


@app.get("/.well-known/openai.yaml", include_in_schema=False)
def well_known_manifest():
    return FileResponse("openai-actions.yaml", media_type="application/yaml")


@app.middleware("http")
async def check_key(request: Request, call_next):
    if request.url.path == "/mcp":
        return await call_next(request)
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(
            status_code=401, content={"error": "Unauthorized - invalid API key"}
        )
    return await call_next(request)


async def generate_mcp_stream():
    """Generator for NDJSON streaming events."""
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
    "/exec/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
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
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/exec")
async def exec_action(payload: dict):
    # TODO: implement modify/open/close logic
    return {"status": "executed", "result": "ok"}


@app.post("/tool/search")
async def search_tool(query: str):
    # TODO: add market search logic
    return {"results": []}



class ActionPayload(BaseModel):
    type: str
    approve: bool = False

async def _handle_read_action(action_type: str):
    """Return stub responses matching OpenAPI schemas."""
    if action_type == "whisper_suggest":
        return {
            "message": "stay curious",
            "heuristics": [],
            "meta": {"user_id": "demo", "symbol": "XAUUSD"},
        }
    if action_type == "session_boot":
        return {
            "trades": [],
            "positions": [],
            "equity": None,
            "risk": None,
        }
    if action_type == "trades_recent":
        return [
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
        ]
    if action_type == "trades_history_mt5":
        return [
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
        ]
    return {"error": "unsupported type"}


@app.get("/api/v1/actions/read")
async def get_actions_read(
    type: str = "session_boot",
    limit: int | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    pnl_min: float | None = None,
    pnl_max: float | None = None,
    user_id: str | None = None,
):
    return await _handle_read_action(type)


@app.post("/api/v1/actions/read")

async def post_actions_read(payload: ActionPayload):
    return await _handle_read_action(payload.type)

async def post_actions_read(payload: dict):
    return await _handle_read_action(payload.get("type", "session_boot"))

@app.get("/api/v1/actions/query")
async def get_actions_query(
    type: str = "session_boot",
    limit: int | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    pnl_min: float | None = None,
    pnl_max: float | None = None,
    user_id: str | None = None,
):
    return await _handle_read_action(type)


@app.post("/api/v1/actions/query")

async def post_actions_query(payload: ActionPayload):
    return await _handle_read_action(payload.type)

async def post_actions_query(payload: dict):
    return await _handle_read_action(payload.get("type", "session_boot"))



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
