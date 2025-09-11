import time
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    generate_latest,
)
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from .routers.tools import router as tools_router
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

app = FastAPI()

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


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    if request.url.path != "/metrics":
        duration = time.perf_counter() - start_time
        REQUEST_COUNTER.labels(request.method, request.url.path).inc()
        REQUEST_LATENCY.labels(request.url.path).observe(duration)
    return response

# Simple Prometheus counter for all HTTP requests
REQUEST_COUNT = Counter("mcp2_requests_total", "Total HTTP requests")


@app.middleware("http")
async def increment_request_count(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.inc()
    return response
REQUESTS = Counter(
    "mcp2_requests_total",
    "Total MCP2 requests",
    ["endpoint"],
    registry=REGISTRY,
)
MCP2_UP = Gauge("mcp2_up", "MCP2 server up status", registry=REGISTRY)


@app.middleware("http")
async def track_requests(request, call_next):
    try:
        REQUESTS.labels(endpoint=request.url.path).inc()
    except Exception:
        pass
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    MCP2_UP.set(1)
    return {'status': 'ok'}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


app.include_router(tools_router)
