#!/usr/bin/env python3
"""Cron job that processes ticks, publishes alerts, and queues simulations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict

import redis

HIGH_RISK_THRESHOLD = 0.9
WHISPERER_QUEUE = "whisperer:simulation"

# ---------------------------------------------------------------------------
# Whisperer Simulation Queue Format
# ---------------------------------
# * Redis data type: List stored at key ``whisperer:simulation``.
# * Each entry: JSON-encoded object::
#
#     {
#         "symbol": str,          # e.g. "EURUSD"
#         "price": float,         # last traded price
#         "risk_score": float,    # model risk score 0..1
#         "timestamp": str        # ISO 8601 UTC timestamp
#     }
#
# Consumers should BRPOP from ``whisperer:simulation`` to retrieve ticks
# in FIFO order and feed them into the Whisperer simulation engine.
# They must handle JSON decoding errors and are responsible for their
# own acknowledgment or retry logic.
# ---------------------------------------------------------------------------


def publish_alert(redis_client: redis.Redis, tick: Dict) -> None:
    """Publish a high-risk tick alert to the alerts channel."""
    alert = {"event": "high_risk_tick", "tick": tick}
    redis_client.publish("telegram-alerts", json.dumps(alert))


def enqueue_for_simulation(redis_client: redis.Redis, tick: Dict) -> None:
    """Queue the high-risk tick for Whisperer offline simulation."""
    redis_client.rpush(WHISPERER_QUEUE, json.dumps(tick))


def process_tick(redis_client: redis.Redis, tick: Dict) -> None:
    """Publish alerts and enqueue ticks when risk exceeds threshold."""
    if tick.get("risk_score", 0) >= HIGH_RISK_THRESHOLD:
        publish_alert(redis_client, tick)
        enqueue_for_simulation(redis_client, tick)


def main() -> int:
    redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
    # Placeholder tick for demonstration. Production code would call the
    # predictive model and iterate over real-time ticks.
    tick = {
        "symbol": "EURUSD",
        "price": 1.2345,
        "risk_score": 0.95,
        "timestamp": datetime.utcnow().isoformat(),
    }
    process_tick(redis_client, tick)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
