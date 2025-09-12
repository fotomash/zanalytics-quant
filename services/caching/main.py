import os
import json
from threading import Thread
from typing import Any, Dict, Optional

import redis
from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from prometheus_client import (
    Counter,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    generate_latest,
)
from services.common import get_logger


KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "caching-service")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "enriched-analysis-payloads")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

LATEST_PAYLOAD_TTL = int(os.getenv("LATEST_PAYLOAD_TTL", "3600"))
ACTIVE_FVG_TTL = int(os.getenv("ACTIVE_FVG_TTL", "3600"))
BEHAVIORAL_SCORE_TTL = int(os.getenv("BEHAVIORAL_SCORE_TTL", "3600"))


app = FastAPI(title="Caching Service")

REDIS_CACHE_HITS = Counter(
    "redis_cache_hits_total",
    "Redis cache hits",
    registry=REGISTRY,
)
REDIS_CACHE_MISSES = Counter(
    "redis_cache_misses_total",
    "Redis cache misses",
    registry=REGISTRY,
)

running = False
worker_thread: Optional[Thread] = None
logger = get_logger(__name__)


def _create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BROKERS,
            "group.id": KAFKA_GROUP,
            "auto.offset.reset": "earliest",
        }
    )


def _create_redis_client() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def _cache_set(r: redis.Redis, key: str, value: str, ttl: int) -> None:
    if r.get(key) is not None:
        REDIS_CACHE_HITS.inc()
    else:
        REDIS_CACHE_MISSES.inc()
    r.setex(key, ttl, value)


def _handle_payload(r: redis.Redis, payload_str: str) -> None:
    try:
        payload: Dict[str, Any] = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return

    symbol: Optional[str] = payload.get("symbol")
    timeframe: Optional[str] = payload.get("timeframe")
    trader_id: Optional[str] = payload.get("trader_id")

    if symbol and timeframe:
        _cache_set(
            r,
            f"latest_payload:{symbol}:{timeframe}",
            payload_str,
            LATEST_PAYLOAD_TTL,
        )

    fvg = payload.get("fvg_signal")
    if symbol and fvg is not None:
        _cache_set(
            r,
            f"active_fvg_signals:{symbol}",
            json.dumps(fvg),
            ACTIVE_FVG_TTL,
        )

    behavioral = payload.get("behavioral_score")
    if trader_id and behavioral is not None:
        _cache_set(
            r,
            f"current_behavioral_score:{trader_id}",
            str(behavioral),
            BEHAVIORAL_SCORE_TTL,
        )

def _consume_loop() -> None:
    consumer = _create_consumer()
    redis_client = _create_redis_client()
    consumer.subscribe([KAFKA_TOPIC])
    logger.info(
        "Caching service consuming '%s' from %s and writing to Redis@%s:%d",
        KAFKA_TOPIC,
        KAFKA_BROKERS,
        REDIS_HOST,
        REDIS_PORT,
    )
    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            logger.error("Consumer error: %s", msg.error())
            continue
        payload_str = msg.value().decode("utf-8")
        _handle_payload(redis_client, payload_str)
    consumer.close()


@app.on_event("startup")
def _startup() -> None:
    global running, worker_thread
    running = True
    worker_thread = Thread(target=_consume_loop, daemon=True)
    worker_thread.start()


@app.on_event("shutdown")
def _shutdown() -> None:
    global running, worker_thread
    running = False
    if worker_thread is not None:
        worker_thread.join(timeout=5)


class HealthStatus(BaseModel):
    status: str
    kafka: bool
    redis: bool


@app.get("/health", response_model=HealthStatus)
def health() -> JSONResponse:
    kafka_ok = False
    redis_ok = False
    try:
        c = _create_consumer()
        c.list_topics(timeout=1.0)
        kafka_ok = True
        c.close()
    except Exception:
        kafka_ok = False
    try:
        r = _create_redis_client()
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    status = "ok" if kafka_ok and redis_ok else "error"
    payload = HealthStatus(status=status, kafka=kafka_ok, redis=redis_ok)
    code = 200 if kafka_ok and redis_ok else 503
    return JSONResponse(status_code=code, content=payload.model_dump())


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
