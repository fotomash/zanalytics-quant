"""Simple Prometheus metrics client."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import requests
import yaml


CONFIG_PATH = Path("config/diagnostics.yaml")


def _load_prometheus_url(config_path: Path = CONFIG_PATH) -> str:
    """Return the Prometheus base URL from config."""
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("prometheus", {}).get("url", "")
    except FileNotFoundError:
        return ""


def fetch_metrics(
    queries: Dict[str, str] | None = None, config_path: Path = CONFIG_PATH
) -> Dict[str, float]:
    """Query Prometheus for the specified metrics.

    Parameters
    ----------
    queries:
        Mapping of human friendly metric names to PromQL queries. If not
        supplied, a default set of metrics is queried.
    config_path:
        Location of the configuration file containing the Prometheus URL.

    Returns
    -------
    dict
        Mapping of metric names to numeric results. Failed lookups return
        ``float('nan')``.
    """
    if queries is None:
        queries = {
            "Messages Processed": "messages_processed_total",
            "Average Processing Latency": "avg_processing_latency_seconds",
        }

    base_url = _load_prometheus_url(config_path)
    results: Dict[str, float] = {}
    for label, promql in queries.items():
        url = f"{base_url.rstrip('/')}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": promql}, timeout=2)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("data", {}).get("result", [])
            if result:
                results[label] = float(result[0]["value"][1])
            else:
                results[label] = float("nan")
        except Exception:
            results[label] = float("nan")
    return results
