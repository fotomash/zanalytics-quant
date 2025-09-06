import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# Title and layout
st.set_page_config(
    page_title="Wyckoff Advanced (Live)",
    page_icon="📡",
    layout="wide"
)

st.title("📡 Wyckoff Advanced Terminal")
st.markdown("Styled real-time chart with Wyckoff overlays and advanced volume/price interaction.")

# Symbol selector
symbol = st.selectbox("Choose Symbol", ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"], index=0)
tick_count = st.slider("Tick History Size", 1000, 10000, 5000, 500)
refresh = st.toggle("Auto Refresh", value=True)

# Connect to MT5 tick API (local)
@st.cache_data(ttl=30)
def get_ticks(symbol, count):
    try:
        endpoints = [
            "http://mt5:8000/ticks",  # internal Docker network
            "http://localhost:5001/ticks"  # fallback to host access
        ]
        for url in endpoints:
            try:
                r = requests.get(url, params={"symbol": symbol, "count": count}, timeout=5)
                r.raise_for_status()
                df = pd.DataFrame(r.json())
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df = df.set_index('time')
                return df
            except Exception as e:
                st.warning(f"Failed to fetch from {url}: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Tick API error: {e}")
        return pd.DataFrame()

def resample_ticks(df, tf='1Min'):
    if df.empty:
        return df
    ohlc = df['last'].resample(tf).ohlc()
    ohlc['volume'] = df['volume'].resample(tf).sum()
    return ohlc.dropna()

ticks_df = get_ticks(symbol, tick_count)
ohlc_df = resample_ticks(ticks_df)

if not ohlc_df.empty:
    fig = go.Figure(data=[go.Candlestick(
        x=ohlc_df.index,
        open=ohlc_df['open'],
        high=ohlc_df['high'],
        low=ohlc_df['low'],
        close=ohlc_df['close'],
        name='Price'
    )])

    fig.add_trace(go.Bar(
        x=ohlc_df.index,
        y=ohlc_df['volume'],
        name='Volume',
        marker_color='rgba(0, 0, 255, 0.3)',
        yaxis='y2'
    ))

    # Optional: style layout like Home.py
    fig.update_layout(
        title=f"{symbol} - Wyckoff Advanced View",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Price"),
        yaxis2=dict(
            title="Volume",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

else:
    st.warning("No data available.")

if refresh:
    time.sleep(30)
    st.rerun()