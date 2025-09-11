"""Service health utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import requests
import yaml

CONFIG_PATH = Path("config/diagnostics.yaml")


def fetch_service_health(
    services: Dict[str, str] | None = None, config_path: Path = CONFIG_PATH
) -> Dict[str, bool]:
    """Fetch /health status from configured services.

    Parameters
    ----------
    services:
        Optional mapping of service names to explicit health endpoints.
        When omitted the mapping is read from ``config_path``.
    config_path:
        Path to the configuration file containing service endpoints.

    Returns
    -------
    dict
        Mapping of service name to boolean health status.
    """
    if services is None:
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            services = cfg.get("services", {})
        except FileNotFoundError:
            services = {}

    results: Dict[str, bool] = {}
    for name, endpoint in services.items():
        url = endpoint if endpoint.endswith("/health") else f"{endpoint.rstrip('/')}/health"
        try:
            resp = requests.get(url, timeout=2)
            results[name] = resp.status_code == 200
        except requests.RequestException:
            results[name] = False
    return results
