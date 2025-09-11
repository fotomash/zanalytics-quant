import os
import json
import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel
import asyncpg
import redis.asyncio as redis


class ToolInfo(BaseModel):
    """Representation of a tool item."""

    id: int
    name: str
    description: str | None = None
    content: str | None = None


class ToolSearchRequest(BaseModel):
    """Request model for tool search."""

    query: str


class ToolSearchResponse(BaseModel):
    """Response model for tool search."""

    results: List[ToolInfo]


class ToolFetchRequest(BaseModel):
    """Request model for fetching tools by id."""

    ids: List[int]


class ToolFetchResponse(BaseModel):
    """Response model containing full tool records."""

    tools: List[ToolInfo]


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter with timestamp and extra fields."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - trivial
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                log_record[key] = value
        return json.dumps(log_record)


logger = logging.getLogger("mcp2")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Zanalytics MCP v2")

API_KEY_HEADER = "X-API-Key"
EXPECTED_API_KEY = os.getenv("MCP2_API_KEY")


async def require_api_key(api_key: str = Header(..., alias=API_KEY_HEADER)) -> str:
    if not EXPECTED_API_KEY or api_key != EXPECTED_API_KEY:
        logger.warning("auth_failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    logger.info("auth_ok")
    return api_key


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
pg_pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup_event() -> None:
    global pg_pool
    logger.info("startup")
    try:
        pg_pool = await asyncpg.create_pool(PG_DSN)
        logger.info("pg_connected")
    except Exception as exc:  # pragma: no cover - connection optional
        logger.warning("pg_connect_failed", extra={"error": str(exc)})
        pg_pool = None


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("shutdown")
    if pg_pool:
        await pg_pool.close()
    await redis_client.close()


@app.get("/health")
async def health() -> dict:
    logger.info("health", extra={"status": "ok"})
    return {"status": "ok"}


@app.post("/mcp/tools/search", dependencies=[Depends(require_api_key)])
async def tools_search(payload: ToolSearchRequest) -> ToolSearchResponse:
    cache_key = f"toolsearch:{payload.query}"
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info("cache_hit", extra={"query": payload.query})
        return ToolSearchResponse.model_validate_json(cached)

    if not pg_pool:
        raise HTTPException(status_code=500, detail="Database unavailable")

    pattern = f"%{payload.query.lower()}%"
    rows = await pg_pool.fetch(
        "SELECT id, name, description FROM tools WHERE LOWER(name) LIKE $1 OR LOWER(description) LIKE $1 ORDER BY id LIMIT 20",
        pattern,
    )
    results = [ToolInfo(id=r["id"], name=r["name"], description=r["description"]) for r in rows]
    response = ToolSearchResponse(results=results)
    await redis_client.set(cache_key, response.model_dump_json(), ex=60)
    logger.info("search", extra={"query": payload.query, "count": len(results)})
    return response


@app.post("/mcp/tools/fetch", dependencies=[Depends(require_api_key)])
async def tools_fetch(payload: ToolFetchRequest) -> ToolFetchResponse:
    if not pg_pool:
        raise HTTPException(status_code=500, detail="Database unavailable")

    tools: List[ToolInfo] = []
    missing: List[int] = []
    for tid in payload.ids:
        cached = await redis_client.get(f"tool:{tid}")
        if cached:
            logger.info("cache_hit", extra={"id": tid})
            tools.append(ToolInfo.model_validate_json(cached))
        else:
            missing.append(tid)

    if missing:
        rows = await pg_pool.fetch(
            "SELECT id, name, description, content FROM tools WHERE id = ANY($1::int[])", missing
        )
        for r in rows:
            info = ToolInfo(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                content=r.get("content"),
            )
            tools.append(info)
            await redis_client.set(f"tool:{info.id}", info.model_dump_json(), ex=300)

    logger.info("fetch", extra={"count": len(tools)})
    return ToolFetchResponse(tools=tools)
