from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from .routers.tools import router as tools_router
from .routers.llm import router as llm_router
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

app = FastAPI()

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


app.include_router(tools_router)
app.include_router(llm_router)
