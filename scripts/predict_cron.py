#!/usr/bin/env python3
"""Cron job that processes ticks, publishes alerts, and queues simulations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Optional
import logging
import re

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


_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _parse_risk(value: object) -> Optional[float]:
    """Parse a risk value that may be numeric or embedded in text.

    Returns a float if successfully parsed, otherwise None.
    """
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if not s:
            return None
        m = _FLOAT_RE.search(s)
        return float(m.group(0)) if m else None
    except Exception:
        return None


def process_tick(redis_client: redis.Redis, tick: Dict) -> None:
    """Publish alerts and enqueue ticks when risk exceeds threshold.

    Tolerates non-numeric risk values by attempting to extract a number; if
    parsing fails, logs at debug level and skips the tick.
    """
    risk = _parse_risk(tick.get("risk_score"))
    if risk is None:
        logging.debug("skip tick without numeric risk: %s", tick)
        return
    # Keep normalized risk on the tick for downstream consumers
    tick["risk_score"] = risk
    if risk >= HIGH_RISK_THRESHOLD:
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

import os
import arrow
import pyarrow as pa

from services.mcp2.llm_config import call_local_echo


def main() -> None:
    """Invoke local echo with a simple prompt."""
    prompt = os.getenv("PREDICT_CRON_PROMPT", "ping")
    timestamp = arrow.utcnow().isoformat()
    _ = pa.array([timestamp])  # ensure pyarrow imported
    print(call_local_echo(prompt))


if __name__ == "__main__":

"""Run prediction cron with configurable risk threshold.

The script reads the risk threshold from the ``RISK_THRESHOLD``
environment variable or from ``config/predict_cron.yaml``.
It also provides a helper to compute a recommended threshold from
historical silence/spike data.
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from statistics import mean, stdev
from typing import List, Optional

import yaml

# Default config path can be overridden for tests or alternate deployments
CONFIG_PATH = Path(os.getenv("PREDICT_CRON_CONFIG", "config/predict_cron.yaml"))


def _load_config_threshold() -> Optional[float]:
    """Load threshold from the YAML config file if available."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            value = data.get("risk_threshold")
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
    return None


def get_risk_threshold() -> float:
    """Return risk threshold from env var or config, defaulting to 0.5."""
    env_val = os.getenv("RISK_THRESHOLD")
    if env_val is not None:
        try:
            return float(env_val)
        except ValueError:
            pass
    config_val = _load_config_threshold()
    if config_val is not None:
        return config_val
    return 0.5


def recommend_threshold(history_path: str) -> float:
    """Compute a recommended threshold from historical data.

    The history file must be a CSV with a ``spike`` column containing
    numeric magnitudes. The recommended threshold is ``mean + 2*stdev``
    of these spike values.
    """
    values: List[float] = []
    with open(history_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                values.append(float(row["spike"]))
            except (KeyError, ValueError):
                # Ignore rows missing or with invalid spike values
                continue
    if not values:
        raise ValueError("no spike data found in history file")
    avg = mean(values)
    sd = stdev(values) if len(values) > 1 else 0.0
    return avg + 2 * sd


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Prediction cron")
    parser.add_argument(
        "--history",
        help="CSV file with past silence/spike data to compute a recommended threshold",
    )
    args = parser.parse_args(argv)

    threshold = get_risk_threshold()
    print(f"Using risk threshold: {threshold}")

    if args.history:
        try:
            recommended = recommend_threshold(args.history)
            print(f"Recommended threshold based on history: {recommended}")
        except Exception as exc:
            print(f"Unable to compute recommended threshold: {exc}")


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
