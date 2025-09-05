"""Phoenix Wyckoff Dashboard

Streamlit page for visualizing Wyckoff scoring using Phoenix-compliant API.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
import requests
import time

# Page Configuration
st.set_page_config(
    page_title="Phoenix Wyckoff Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API Configuration
MT5_API_URL = "http://localhost:8000"  # MT5 backend
PULSE_API_URL = "http://localhost:8000/api/pulse"  # Phoenix Pulse API

def fetch_tick_data(symbol: str, count: int = 5000) -> pd.DataFrame:
    """Fetch raw tick data from MT5 API"""
    params = {"symbol": symbol, "count": count}
    try:
        response = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not data:
            st.warning(f"No ticks for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        # Handle timestamp (assuming 'time' is UNIX seconds)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("timestamp").sort_index()

        # Determine price
        if "last" in df and df["last"].notna().any():
            df["price"] = df["last"]
        elif "bid" in df and "ask" in df:
            df["price"] = (df["bid"] + df["ask"]) / 2
        else:
            st.error("No valid price fields in ticks")
            return pd.DataFrame()

        # Ensure volume column exists
        if "volume" not in df:
            df["volume"] = 1.0
        return df
    except Exception as e:  # pragma: no cover - network errors
        st.error(f"MT5 API error: {e}")
        return pd.DataFrame()

def aggregate_to_bars(df: pd.DataFrame, timeframe: str = "1min") -> pd.DataFrame:
    """Aggregate ticks to OHLCV bars"""
    if df.empty:
        return pd.DataFrame()

    bars = df["price"].resample(timeframe).ohlc()
    bars["volume"] = df["volume"].resample(timeframe).sum()
    bars = bars.dropna()
    return bars

def score_wyckoff_via_api(bars_df: pd.DataFrame) -> dict:
    """Consume Phoenix-compliant scorer via API"""
    if bars_df.empty:
        return {}

    bars_list = [
        {
            "ts": str(idx),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for idx, row in bars_df.iterrows()
    ]
    payload = {"bars": bars_list}
    try:
        response = requests.post(
            f"{PULSE_API_URL}/wyckoff/score", json=payload, timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:  # pragma: no cover - network errors
        st.error(f"Scorer API error: {e}")
        return {}

# Sidebar
with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"])
    tick_count = st.slider("Ticks", 1000, 10000, 5000)
    timeframe = st.selectbox("Timeframe", ["30s", "1min", "5min"])
    auto_refresh = st.toggle("Auto Refresh (30s)", value=True)

# Main Dashboard
st.title("Phoenix Wyckoff Dashboard")

# Fetch & Aggregate
ticks = fetch_tick_data(symbol, tick_count)
if not ticks.empty:
    bars = aggregate_to_bars(ticks, timeframe)

    # Score via API
    score = score_wyckoff_via_api(bars)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score", score.get("score", 0))
    col2.metric("Phase", score.get("phase", "Neutral"))
    col3.metric("Spring", "✓" if score.get("spring", False) else "-")
    col4.metric("News Mask", "Active" if score.get("news_mask", False) else "Inactive")

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    fig.add_trace(
        go.Candlestick(
            x=bars.index,
            open=bars["open"],
            high=bars["high"],
            low=bars["low"],
            close=bars["close"],
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars["close"],
            mode="markers",
            marker_color="green" if score.get("spring", False) else "red",
            name="Event",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Bar(x=bars.index, y=bars["volume"]), row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

    # Reasons/Explain
    st.subheader("Explain")
    st.json(score.get("explain", {}))

    # Probabilities
    st.subheader("Probs")
    probs = score.get("p", [0.25] * 4)
    fig_prob = px.pie(values=probs, names=["Acc", "Mup", "Dist", "Mdk"])
    st.plotly_chart(fig_prob)
else:
    st.info("No ticks fetched")

if auto_refresh:
    time.sleep(30)
    st.rerun()
