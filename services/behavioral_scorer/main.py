"""Behavioral scorer service.

Consumes analysis and trade events from Kafka, tracks basic behavioral
metrics per trader, and publishes scores to Redis.
"""
from __future__ import annotations

import json
import os
import signal
import time
from collections import deque
from typing import Any, Dict

import redis
from confluent_kafka import Consumer, KafkaError

from services.common.redis_utils import set_behavioral_score


KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SCORE_INTERVAL = int(os.getenv("SCORE_INTERVAL", "60"))

# Rapid trade detection configuration
RAPID_TRADE_WINDOW = int(os.getenv("RAPID_TRADE_WINDOW", "60"))  # seconds
RAPID_TRADE_THRESHOLD = int(os.getenv("RAPID_TRADE_THRESHOLD", "3"))
PATIENCE_PENALTY = float(os.getenv("PATIENCE_PENALTY", "0.1"))

TOPICS = ["final-analysis-payloads", "trade-execution-events"]


def record_trade(trader_state: Dict[str, Any], timestamp: float) -> None:
    """Record a trade timestamp and update patience metrics."""

    trades = trader_state.setdefault("executions", deque())
    trades.append(timestamp)

    # Drop timestamps outside the configured window
    while trades and timestamp - trades[0] > RAPID_TRADE_WINDOW:
        trades.popleft()

    if len(trades) > RAPID_TRADE_THRESHOLD:
        trader_state["rapid_trade"] = True
        trader_state["patience_score"] = max(
            0.0, trader_state.get("patience_score", 1.0) - PATIENCE_PENALTY
        )
    else:
        trader_state["rapid_trade"] = False

    trader_state["last_trade"] = timestamp


def main() -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": os.getenv("BEHAVIORAL_GROUP", "behavioral-scorer"),
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe(TOPICS)

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    state: Dict[str, Dict[str, Any]] = {}
    last_emit = time.time()
    shutdown = False

    def _handle_shutdown(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    def emit_scores() -> None:
        now = time.time()
        for trader_id, info in state.items():
            last_trade = info.get("last_trade")
            inactivity = now - last_trade if last_trade else None
            payload = {
                "last_trade": last_trade,
                "analysis_count": info.get("analysis_count", 0),
                "inactive_seconds": inactivity,
                "patience_index": info.get("patience_score", 1.0),
                "rapid_trades": info.get("rapid_trade", False),
            }
            set_behavioral_score(r, trader_id, payload)

    try:
        while not shutdown:
            msg = consumer.poll(1.0)
            if msg is None:
                if time.time() - last_emit >= SCORE_INTERVAL:
                    emit_scores()
                    last_emit = time.time()
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"kafka error: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except Exception:
                consumer.commit(msg)
                continue

            trader_id = payload.get("trader_id") or payload.get("traderId")
            if not trader_id:
                consumer.commit(msg)
                continue

            trader_state = state.setdefault(trader_id, {"patience_score": 1.0, "executions": deque()})
            if msg.topic() == "trade-execution-events":
                record_trade(trader_state, time.time())
            elif msg.topic() == "final-analysis-payloads":
                trader_state["analysis_count"] = trader_state.get("analysis_count", 0) + 1

            consumer.commit(msg)

            if time.time() - last_emit >= SCORE_INTERVAL:
                emit_scores()
                last_emit = time.time()
    finally:
        emit_scores()
        consumer.close()
        try:
            r.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
