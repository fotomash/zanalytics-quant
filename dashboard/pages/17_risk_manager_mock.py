import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json
import redis
import time
from typing import Dict, Optional, List
from datetime import datetime

# --- Config (from .env/secrets.toml; repo .env.example) ---
MT5_API_URL = st.secrets.get("MT5_API_URL", "http://localhost:8000")
PULSE_API_URL = st.secrets.get("PULSE_API_URL", "http://localhost:8000/api/pulse")
REDIS_URL = st.secrets.get("REDIS_URL", "redis://localhost:6379/0")

# Redis for streaming
@st.cache_resource
def get_redis():
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        return r
    except:
        st.warning("Redis unavailable")
        return None

redis_client = get_redis()

# Fetch ticks
@st.cache_data(ttl=30)
def fetch_ticks(symbol: str, count: int = 5000) -> pd.DataFrame:
    params = {'symbol': symbol, 'limit': count}
    try:
        r = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df = df.set_index('timestamp').sort_index()
        # Price: last or mid
        if 'last' in df:
            df['price'] = df['last'].fillna((df['bid'] + df['ask']) / 2 if 'bid' in df and 'ask' in df else np.nan)
        elif 'bid' in df and 'ask' in df:
            df['price'] = (df['bid'] + df['ask']) / 2
        # Volume: volume or 1/tick
        df['volume'] = df.get('volume', 1.0)
        return df
    except Exception as e:
        st.error(f"MT5 /ticks error: {e}")
        # Mock fallback
        mock_idx = pd.date_range(datetime.now() - timedelta(minutes=count//10), periods=count, freq='6S')
        return pd.DataFrame({
            'price': np.random.normal(1.085, 0.001, count).cumsum(),
            'volume': np.random.randint(1, 10, count)
        }, index=mock_idx)

# Aggregate to bars
def aggregate_bars(df: pd.DataFrame, tf: str = '1min') -> pd.DataFrame:
    if df.empty:
        return df
    bars = df['price'].resample(tf).ohlc()
    bars['volume'] = df['volume'].resample(tf).sum()
    return bars.dropna()

# Call scorer API
def call_scorer(bars: pd.DataFrame) -> Dict:
    if bars.empty:
        return {}
    payload = {'bars': bars.reset_index().to_dict('records')}
    try:
        r = requests.post(f"{PULSE_API_URL}/wyckoff/score", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Scorer error: {e}")
        return {'score': 50, 'phase': 'Neutral', 'p': [0.25]*4, 'spring': False, 'news_mask': False, 'explain': {}, 'reasons': ['Fallback mode']}

# MTF conflict
def mtf_conflict(labels_1m: str, labels_5m: str, labels_15m: str) -> bool:
    if not all([labels_1m, labels_5m, labels_15m]):
        return False
    bull_htf = labels_5m in ["Markup", "Accumulation"] or labels_15m in ["Markup", "Accumulation"]
    bear_htf = labels_5m in ["Markdown", "Distribution"] or labels_15m in ["Markdown", "Distribution"]
    return (labels_1m == "Distribution" and bull_htf) or (labels_1m == "Accumulation" and bear_htf)

# UI
st.title("Phoenix Wyckoff Dashboard - Live MT5 Ticks")

# Sidebar
with st.sidebar:
    symbol = st.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"])
    tick_count = st.slider("Ticks", 2000, 20000, 5000)
    timeframe = st.selectbox("Timeframe", ["1min", "5min", "15min"])
    auto_refresh = st.toggle("Auto Refresh (30s)", value=True)
    win = st.slider("Window", 20, 100, 50)

# Fetch/Aggregate/Score
ticks = fetch_ticks(symbol, tick_count)
if not ticks.empty:
    bars_1m = aggregate_bars(ticks, '1min')
    bars_5m = aggregate_bars(ticks, '5min')
    bars_15m = aggregate_bars(ticks, '15min')
    bars_pm = aggregate_bars(ticks, timeframe)

    score_1m = call_scorer(bars_1m)
    score_5m = call_scorer(bars_5m)
    score_15m = call_scorer(bars_15m)
    score_pm = call_scorer(bars_pm)

    # MTF labels/conflict
    l1 = score_1m.get('phase', 'Neutral')
    l5 = score_5m.get('phase', 'Neutral')
    l15 = score_15m.get('phase', 'Neutral')
    conflict = mtf_conflict(l1, l5, l15)

    # Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Score", score_pm.get('score', 0))
    col2.metric("Phase", score_pm.get('phase', 'Neutral'))
    col3.metric("Spring", "✓" if score_pm.get('spring', False) else "-")
    col4.metric("News Mask", "Active" if score_pm.get('news_mask', False) else "Inactive")
    col5.metric("MTF Conflict", "Yes" if conflict else "No")

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])

    # Candlestick
    fig.add_trace(go.Candlestick(x=bars_pm.index, open=bars_pm['open'], high=bars_pm['high'],
                                 low=bars_pm['low'], close=bars_pm['close']), row=1, col=1)

    # Volume
    fig.add_trace(go.Bar(x=bars_pm.index, y=bars_pm['volume'], name="Volume"), row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

    # Reasons/Explain
    st.subheader("Explain")
    st.json(score_pm.get('explain', {}))

    # Probs
    st.subheader("Probs")
    probs = score_pm.get('p', [0.25]*4)
    fig_prob = px.pie(values=probs, names=["Acc", "Mup", "Dist", "Mdk"])
    st.plotly_chart(fig_prob)

else:
    st.info("No ticks fetched")

if auto_refresh:
    time.sleep(30)
    st.experimental_rerun()