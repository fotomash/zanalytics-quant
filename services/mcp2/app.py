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
from .routers.tools import router as tools_router

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


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


app.include_router(tools_router)
