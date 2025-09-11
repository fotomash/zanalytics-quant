from fastapi import FastAPI, Response
from .routers.tools import router as tools_router
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

app = FastAPI()

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


@app.get('/health')
async def health():
    MCP2_UP.set(1)
    return {'status': 'ok'}


@app.get('/metrics')
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


app.include_router(tools_router)
