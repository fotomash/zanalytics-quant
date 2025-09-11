from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from .routers.tools import router as tools_router

app = FastAPI()

# Simple Prometheus counter for all HTTP requests
REQUEST_COUNT = Counter("mcp2_requests_total", "Total HTTP requests")


@app.middleware("http")
async def increment_request_count(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.inc()
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(tools_router)
