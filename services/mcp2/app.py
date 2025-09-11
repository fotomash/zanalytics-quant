import os
import time

from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)

from .auth import verify_api_key
from .routers.llm import router as llm_router
from .routers.echonudge import router as echonudge_router
from .routers.ab import router as ab_router
from .routers.manifest import router as manifest_router
from .routers.streams import router as streams_router
from .routers.tools import router as tools_router


dependencies = [Depends(verify_api_key)] if os.getenv("MCP2_API_KEY") else []
app = FastAPI(dependencies=dependencies)

REQUEST_COUNTER = Counter(
    "mcp2_requests_total",
    "Total number of requests received by MCP2",
    ["method", "endpoint"],
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "mcp2_request_latency_seconds",
    "Request latency in seconds for MCP2",
    ["endpoint"],
    registry=REGISTRY,
)

MCP2_UP = Gauge("mcp2_up", "MCP2 server up status", registry=REGISTRY)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    if request.url.path != "/metrics":
        duration = time.perf_counter() - start_time
        REQUEST_COUNTER.labels(request.method, request.url.path).inc()
        REQUEST_LATENCY.labels(request.url.path).observe(duration)
    return response


@app.get("/health")
async def health():
    MCP2_UP.set(1)
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


app.include_router(tools_router)
app.include_router(llm_router)
app.include_router(streams_router)
app.include_router(echonudge_router)
app.include_router(ab_router)
app.include_router(manifest_router)
