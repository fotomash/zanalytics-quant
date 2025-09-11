"""Streamlit dashboard for live ML metrics from Redis.

Run the app:
    streamlit run integration/streamlit_ml_dashboard.py

Configuration can be provided via environment variables or the sidebar:
    STREAMLIT_REDIS_HOST        Redis host (default ``localhost``)
    STREAMLIT_REDIS_PORT        Redis port (default ``6379``)
    STREAMLIT_METRIC_KEYS       Comma-separated keys to monitor
                                (default ``ml:latency,ml:throughput``)
    STREAMLIT_REFRESH_INTERVAL  Refresh interval in seconds (default ``5``)

The app displays the latest numeric values stored under the specified Redis keys
and refreshes automatically at the configured interval.
"""

from dataclasses import dataclass, field
import os
import time
from typing import Dict, List

import redis
import streamlit as st
from dashboard.components import create_metric_donut


@dataclass
class AppConfig:
    """Configuration for connecting to Redis and updating the dashboard."""

    redis_host: str = os.getenv("STREAMLIT_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("STREAMLIT_REDIS_PORT", "6379"))
    metric_keys: List[str] = field(
        default_factory=lambda: [
            key.strip()
            for key in os.getenv(
                "STREAMLIT_METRIC_KEYS", "ml:latency,ml:throughput"
            ).split(",")
            if key.strip()
        ]
    )
    refresh_interval: int = int(os.getenv("STREAMLIT_REFRESH_INTERVAL", "5"))


def get_connection(cfg: AppConfig) -> redis.Redis:
    """Create a Redis connection using the supplied configuration."""

    return redis.Redis(host=cfg.redis_host, port=cfg.redis_port, decode_responses=True)


def fetch_metrics(conn: redis.Redis, keys: List[str]) -> Dict[str, float]:
    """Fetch and convert metrics from Redis into a mapping of key -> float."""

    values = conn.mget(keys)
    metrics: Dict[str, float] = {}
    for key, value in zip(keys, values):
        try:
            metrics[key] = float(value) if value is not None else None
        except (TypeError, ValueError):
            metrics[key] = None
    return metrics


def main() -> None:
    """Launch the Streamlit dashboard and auto-refresh metrics."""

    st.set_page_config(page_title="ML Metrics Dashboard", layout="wide")

    cfg = AppConfig()
    with st.sidebar:
        st.header("Configuration")
        cfg.redis_host = st.text_input("Redis host", cfg.redis_host)
        cfg.redis_port = st.number_input("Redis port", value=cfg.redis_port, step=1)
        metrics_input = st.text_input(
            "Metric keys (comma separated)", ",".join(cfg.metric_keys)
        )
        cfg.metric_keys = [k.strip() for k in metrics_input.split(",") if k.strip()]
        cfg.refresh_interval = st.number_input(
            "Refresh interval (seconds)", min_value=1, value=cfg.refresh_interval
        )

    try:
        conn = get_connection(cfg)
        metrics = fetch_metrics(conn, cfg.metric_keys)
    except redis.RedisError as exc:  # pragma: no cover - display errors at runtime
        st.error(f"Redis connection error: {exc}")
        metrics = {}

    st.title("Live ML Metrics")
    palette = ["#10B981", "#3B82F6", "#F59E0B", "#8B5CF6", "#EF4444", "#14B8A6"]
    for idx, (name, value) in enumerate(metrics.items()):
        color = palette[idx % len(palette)]
        val = value if value is not None else 0
        fig = create_metric_donut(val, name, color, suffix="")
        st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False})

    time.sleep(cfg.refresh_interval)
    st.experimental_rerun()


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    main()
