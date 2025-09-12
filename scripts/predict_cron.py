#!/usr/bin/env python3
"""Cron job that processes ticks, publishes alerts, and queues simulations."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Optional, List, Union

import redis
import yaml
WHISPERER_QUEUE = "whisperer:simulation"
CONFIG_PATH = Path(os.getenv("PREDICT_CRON_CONFIG", "config/predict_cron.yaml"))

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
    redis_client.publish("discord-alerts", json.dumps(alert))


def enqueue_for_simulation(redis_client: redis.Redis, tick: Dict) -> None:
    """Queue the high-risk tick for Whisperer offline simulation."""
    redis_client.rpush(WHISPERER_QUEUE, json.dumps(tick))


_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _parse_risk(value: object) -> Optional[float]:
    """Parse a risk value that may be numeric or embedded in text.

    Returns a float if successfully parsed, otherwise None.

    Examples (doctest):
        >>> _parse_risk(0.87)
        0.87
        >>> _parse_risk("0.42")
        0.42
        >>> _parse_risk("risk=0.93; status=hi")
        0.93
        >>> _parse_risk("85%")
        0.85
        >>> _parse_risk("42")
        0.42
        >>> _parse_risk(None) is None
        True
        >>> _parse_risk("") is None
        True
        >>> _parse_risk("n/a") is None
        True
    """
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            num = float(value)
            has_percent = False
        else:
            s = str(value).strip()
            if not s:
                return None
            m = _FLOAT_RE.search(s)
            if not m:
                return None
            num = float(m.group(0))
            has_percent = "%" in s
        if has_percent or num > 1:
            num /= 100.0
        return num
    except Exception:
        return None


def compute_silence_duration(timestamp: Union[str, int, float]) -> float:
    """Return seconds elapsed since ``timestamp``.

    The ``timestamp`` may be an ISO 8601 string or a Unix epoch expressed as
    either a number or numeric string.  The current time is determined using
    :func:`datetime.utcnow`.  A ``ValueError`` is raised if the timestamp cannot
    be parsed.
    """
    now = datetime.utcnow()

    try:
        if isinstance(timestamp, (int, float)):
            tick_dt = datetime.utcfromtimestamp(float(timestamp))
        else:
            ts = str(timestamp).strip()
            if not ts:
                raise ValueError("empty timestamp")
            try:
                tick_dt = datetime.utcfromtimestamp(float(ts))
            except ValueError:
                tick_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if tick_dt.tzinfo is not None:
                    tick_dt = tick_dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception as exc:
        raise ValueError(f"Malformed timestamp: {timestamp!r}") from exc

    return (now - tick_dt).total_seconds()


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


# Determine the risk threshold once at startup.
# It can be overridden via the ``RISK_THRESHOLD`` environment variable or by
# setting ``risk_threshold`` in ``config/predict_cron.yaml``. See
# ``docs/update_risk_threshold.md`` for details.
RISK_THRESHOLD = get_risk_threshold()


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


def process_tick(
    redis_client: redis.Redis, tick: Dict, threshold: float = RISK_THRESHOLD
) -> None:
    """Publish alerts and enqueue ticks when risk exceeds ``threshold``.

    Tolerates non-numeric risk values by attempting to extract a number; if
    parsing fails, logs at debug level and skips the tick.
    """
    risk = _parse_risk(tick.get("risk_score"))
    if risk is None:
        logging.debug("skip tick without numeric risk: %s", tick)
        return
    # Keep normalized risk on the tick for downstream consumers
    tick["risk_score"] = risk
    if risk >= threshold:
        publish_alert(redis_client, tick)
        enqueue_for_simulation(redis_client, tick)

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Prediction cron")
    parser.add_argument(
        "--history",
        help="CSV file with past silence/spike data to compute a recommended threshold",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a demo tick through the alert pipeline",
    )
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--price", type=float, default=1.2345)
    parser.add_argument("--risk", default="0.95", help="Risk value or text containing it")
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://redis:6379/0"))
    args = parser.parse_args(argv)

    threshold = RISK_THRESHOLD
    print(f"Using risk threshold: {threshold}")

    if args.history:
        try:
            recommended = recommend_threshold(args.history)
            print(f"Recommended threshold based on history: {recommended}")
        except Exception as exc:
            print(f"Unable to compute recommended threshold: {exc}")

    if args.demo:
        try:
            r = redis.from_url(args.redis_url, decode_responses=True)
        except Exception as exc:
            print(f"Unable to connect to Redis: {exc}")
            return
        risk_val = _parse_risk(args.risk) or 0.0
        tick = {
            "symbol": args.symbol,
            "price": float(args.price),
            "risk_score": risk_val,
            "timestamp": datetime.utcnow().isoformat(),
        }
        process_tick(r, tick, threshold=threshold)


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
