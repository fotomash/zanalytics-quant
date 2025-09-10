from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
import httpx
import os
import time

app = FastAPI(title="Zanalytics MCP Server")

INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://django:8000")


async def generate_mcp_stream():
    """Generator for NDJSON streaming events."""
    yield json.dumps({
        "event": "open",
        "data": {"status": "ready", "timestamp": time.time()},
    }) + "\n"

    while True:
        yield json.dumps({
            "event": "heartbeat",
            "data": {"time": time.time(), "server": "mcp1.zanalytics.app"},
        }) + "\n"
        await asyncio.sleep(30)


@app.get("/mcp")
async def mcp_stream():
    return StreamingResponse(
        generate_mcp_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.api_route("/exec/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def exec_proxy(request: Request, full_path: str):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=f"{INTERNAL_API_BASE}/{full_path}",
                json=await request.json() if request.method != "GET" else None,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]},
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Internal API unreachable")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    content_type = resp.headers.get("content-type", "")
    return resp.json() if content_type.startswith("application/json") else {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
