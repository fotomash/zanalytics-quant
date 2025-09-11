import os
from typing import Any, Dict

import requests
import streamlit as st

__all__ = ["diagnostics_panel", "AGGREGATOR_URL", "default_url"]

# Default URL for the health aggregator service
# Deployers can override this via the HEALTH_AGGREGATOR_URL environment variable
# to point at their monitoring stack.
default_url = "http://localhost:8000/health"
AGGREGATOR_URL = os.environ.get("HEALTH_AGGREGATOR_URL", default_url)

def fetch_health(url: str = AGGREGATOR_URL) -> Dict[str, Any]:
    """Fetch health data from the aggregator service.

    Parameters
    ----------
    url:
        Base URL of the health aggregator service.
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        # Avoid breaking the dashboard if the aggregator is unreachable
        return {"status": "unavailable"}

def diagnostics_panel() -> None:
    """Render a simple diagnostics panel using aggregated health data."""
    st.subheader("System Health")
    st.json(fetch_health())
