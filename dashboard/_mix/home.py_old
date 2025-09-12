import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
import requests
import redis
import time
from sqlalchemy import create_engine, text
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv

# --- Page setup ---
st.set_page_config(
    page_title="Zanalytics Home Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Config (no hard-coded creds)
MT5_API_URL = os.getenv("MT5_API_URL", "http://localhost:8000")
PULSE_API_URL = os.getenv("PULSE_API_URL", "http://localhost:8000/api/pulse")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/db")

# Initialize connections
@st.cache_resource
def init_redis():
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        return r
    except Exception:
        st.warning("Redis unavailable - no caching")
        return None

@st.cache_resource
def init_db():
    try:
        engine = create_engine(POSTGRES_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        st.warning("Postgres unavailable - no persistent storage")
        return None

redis_client = init_redis()
db_engine = init_db()

# Cache key helper
def cache_key(symbol: str, tf: str = "1min") -> str:
    return f"enriched_bars:{symbol}:{tf}"

# Fetch & enrich & cache
@st.cache_data(ttl=60)
def get_enriched_bars(symbol: str, count: int = 5000, tf: str = "1min") -> pd.DataFrame:
    # Try Redis cache first
    if redis_client:
        cached = redis_client.get(cache_key(symbol, tf))
        if cached:
            try:
                return pd.read_json(cached, orient="split")
            except Exception:
                pass

    # Fetch ticks
    params = {"symbol": symbol, "limit": count}
    try:
        r = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("timestamp").sort_index()
        # Price: last or mid
        if "last" in df:
            df["price"] = df["last"].fillna((df["bid"] + df["ask"]) / 2 if "bid" in df and "ask" in df else np.nan)
        elif "bid" in df and "ask" in df:
            df["price"] = (df["bid"] + df["ask"]) / 2
        # Volume: volume or 1/tick
        df["volume"] = df.get("volume", 1.0)
    except Exception as e:
        st.error(f"MT5 /ticks error: {e}")
        return pd.DataFrame()

    # Aggregate to bars
    bars = df["price"].resample(tf).ohlc()
    bars["volume"] = df["volume"].resample(tf).sum()
    bars = bars.dropna()

    # Enrich (from utils/enrich_features.py logic - simplified)
    win = 50
    bars["ret"] = bars["close"].pct_change()
    bars["vol_z"] = (bars["volume"] - bars["volume"].rolling(win).mean()) / bars["volume"].rolling(win).std().fillna(1)
    ma = bars["close"].rolling(win).mean()
    sd = bars["close"].rolling(win).std()
    lower = ma - 2 * sd
    upper = ma + 2 * sd

    def _nz(a, fill=0.0):
        return np.nan_to_num(a, nan=fill, posinf=fill, neginf=fill)

    bars["bb_pctB"] = _nz((bars["close"] - lower) / (upper - lower + 1e-6))
    bars["effort"] = _nz(bars["vol_z"])
    bars["result"] = _nz(bars["ret"].abs().rolling(3).mean())
    bars["effort_result_ratio"] = _nz(bars["effort"]) / (_nz(bars["result"]) + 1e-6)
    bars["news_event"] = bars["vol_z"].abs() > 3.0  # Simple news buffer

    # Cache enriched
    if redis_client:
        redis_client.set(cache_key(symbol, tf), bars.to_json(orient="split"), ex=300)
    if db_engine:
        try:
            bars.to_sql(f"enriched_bars_{symbol}_{tf}", db_engine, if_exists="replace")
        except Exception:
            pass

    return bars

# MTF conflict (placeholder - integrate wyckoff_agents)
def mtf_conflict(l1: str, l5: str, l15: str) -> bool:
    return False  # Implement as per agents

# Dashboard
st.title("Zanalytics Home Dashboard - Real-Time MT5 Feed")

# Sidebar
with st.sidebar:
    symbol = st.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"])
    tick_count = st.slider("Ticks", 2000, 20000, 5000)
    timeframe = st.selectbox("Timeframe", ["1min", "5min", "15min"])
    auto_refresh = st.toggle("Auto Refresh (30s)", value=True)

# Fetch/Enrich/Cache
enriched = get_enriched_bars(symbol, tick_count, timeframe)

if not enriched.empty:
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Close", enriched["close"].iloc[-1])
    col2.metric("Volume Z", enriched["vol_z"].iloc[-1])
    col3.metric("BB %B", enriched["bb_pctB"].iloc[-1])
    col4.metric("Effort/Result", enriched["effort_result_ratio"].iloc[-1])

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig.add_trace(
        go.Candlestick(
            x=enriched.index,
            open=enriched["open"],
            high=enriched["high"],
            low=enriched["low"],
            close=enriched["close"],
        ),
        row=1,
        col=1,
    )
    fig.add_trace(go.Bar(x=enriched.index, y=enriched["volume"]), row=2, col=1)
    fig.update_layout(height=600)
    st.plotly_chart(fig)

    # Data
    with st.expander("Enriched Bars"):
        st.dataframe(enriched)
else:
    st.info("No data - check MT5 API")

if auto_refresh:
    time.sleep(30)
    st.rerun()
