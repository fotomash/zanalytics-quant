"""Streamlit ML dashboard for visualizing ML bridge outputs from Redis streams.

This dashboard subscribes to the streams produced by the Redis ML bridge:
- ``ml:signals`` for full model outputs
- ``ml:risk`` for risk-only updates

Users can select which metrics to chart and control the auto-refresh interval
from the sidebar. Redis connections are cached for efficiency.

Run locally:
    streamlit run dashboard/ml_dashboard.py
"""

from dataclasses import dataclass, field
import os
import time
from typing import Dict, List

import pandas as pd
import plotly.express as px
import redis
import streamlit as st


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class AppConfig:
    """Configuration for the ML dashboard."""

    redis_host: str = os.getenv("STREAMLIT_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("STREAMLIT_REDIS_PORT", "6379"))
    signal_stream: str = os.getenv("ML_SIGNAL_STREAM", "ml:signals")
    risk_stream: str = os.getenv("ML_RISK_STREAM", "ml:risk")
    metrics: List[str] = field(default_factory=lambda: ["risk", "alpha", "confidence"])
    refresh_interval: int = int(os.getenv("STREAMLIT_REFRESH_INTERVAL", "5"))


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------
@st.cache_resource
def get_connection(host: str, port: int) -> redis.Redis:
    """Cache and return a Redis connection."""

    return redis.Redis(host=host, port=port, decode_responses=True)


def read_stream(conn: redis.Redis, stream: str, limit: int = 200) -> pd.DataFrame:
    """Read the most recent entries from a Redis stream into a DataFrame."""

    try:
        entries = conn.xrevrange(stream, count=limit)
    except redis.RedisError:
        return pd.DataFrame()
    data: List[Dict[str, str]] = []
    for _, fields in reversed(entries):  # chronological order
        data.append(fields)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    for col in ["risk", "alpha", "confidence"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Streamlit app
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="ML Metrics Dashboard", layout="wide")

    cfg = AppConfig()
    with st.sidebar:
        st.header("Controls")
        cfg.redis_host = st.text_input("Redis host", cfg.redis_host)
        cfg.redis_port = st.number_input("Redis port", value=cfg.redis_port, step=1)
        cfg.signal_stream = st.text_input("Signal stream", cfg.signal_stream)
        cfg.risk_stream = st.text_input("Risk stream", cfg.risk_stream)
        cfg.metrics = st.multiselect(
            "Metrics", options=["risk", "alpha", "confidence"], default=cfg.metrics
        )
        cfg.refresh_interval = st.number_input(
            "Refresh interval (seconds)", min_value=1, value=cfg.refresh_interval
        )

    conn = get_connection(cfg.redis_host, cfg.redis_port)
    signals_df = read_stream(conn, cfg.signal_stream)
    risk_df = read_stream(conn, cfg.risk_stream)

    st.title("ML Metrics Dashboard")

    if signals_df.empty:
        st.info("No signal data available yet.")
    else:
        for metric in cfg.metrics:
            if metric in signals_df.columns:
                fig = px.line(
                    signals_df,
                    x="timestamp",
                    y=metric,
                    color="symbol",
                    title=f"{metric.title()} over time",
                )
                st.plotly_chart(fig, use_container_width=True)

    st.subheader("Current Risk")
    if risk_df.empty:
        st.info("No risk data available yet.")
    else:
        latest = (
            risk_df.sort_values("timestamp").groupby("symbol").tail(1)
        )
        cols = st.columns(len(latest))
        for col, (_, row) in zip(cols, latest.iterrows()):
            val = row.get("risk")
            col.metric(row.get("symbol", "?"), f"{val:.4f}" if val is not None else "—")

    time.sleep(cfg.refresh_interval)
    st.experimental_rerun()


if __name__ == "__main__":  # pragma: no cover
    main()
