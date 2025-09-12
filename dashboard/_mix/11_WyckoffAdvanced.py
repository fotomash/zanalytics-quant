import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import time
import os
from dashboard.components.ui_concentric import concentric_ring

# Title and layout
st.set_page_config(
    page_title="Wyckoff Advanced (Live)",
    page_icon="📡",
    layout="wide"
)

st.title("📡 Wyckoff Advanced Terminal")

# MT5 bridge health strip
def _mt5_health(timeout: float = 1.2) -> bool:
    for url in ("http://mt5:8000/health", "http://localhost:5001/account_info"):
        try:
            r = requests.get(url, timeout=timeout)
            if r.ok:
                return True
        except Exception:
            continue
    return False

mt5_ok = _mt5_health()
st.caption(f"MT5 bridge: {'✅ OK' if mt5_ok else '⚠️ Unavailable'}")
st.markdown("Styled real-time chart with Wyckoff overlays and advanced volume/price interaction.")

# Quick concentric session ring under the header (live endpoints)
try:
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    acct = requests.get(f"{base}/api/v1/account/info", timeout=1.2).json()
    risk = requests.get(f"{base}/api/v1/account/risk", timeout=1.2).json()
    trade = requests.get(f"{base}/api/v1/feed/trade", timeout=1.2).json()
    equity = requests.get(f"{base}/api/v1/feed/equity", timeout=1.2).json()

    eq = float(acct.get('equity') or 0.0)
    sod = float(risk.get('sod_equity') or acct.get('balance') or eq or 0.0)
    pnl_today = eq - sod
    target = float(risk.get('target_amount') or 0.0)
    loss = float(risk.get('loss_amount') or 0.0)

    outer = None
    if pnl_today >= 0 and target > 0:
        outer = min(1.0, pnl_today / target)
    elif pnl_today < 0 and loss > 0:
        outer = -min(1.0, abs(pnl_today) / loss)

    realized = trade.get('realized_usd') if isinstance(trade, dict) else None
    unreal = trade.get('unrealized_usd') if isinstance(trade, dict) else None
    cap_val = max(1.0, abs((realized or 0)) + abs((unreal or 0)))
    left = (abs(unreal) / cap_val) if isinstance(unreal, (int, float)) and cap_val > 0 else 0.0
    right = (abs(realized) / cap_val) if isinstance(realized, (int, float)) and cap_val > 0 else 0.0

    exp = equity.get('exposure_pct') if isinstance(equity, dict) else None
    if isinstance(exp, (int, float)) and exp > 1:
        exp = exp / 100.0

    # Build target/loss markers for outer ring parity with page 04
    ticks = []
    if target and target > 0:
        ticks.append({
            "ring": "outer",
            "angle_norm": 1.0,
            "color": "#22C55E",
            "style": "solid",
            "hover": f"Daily target ${target:,.0f}",
        })
    if loss and loss > 0:
        ticks.append({
            "ring": "outer",
            "angle_norm": -1.0,
            "color": "#EF4444",
            "style": "solid",
            "hover": f"Daily loss cap ${loss:,.0f}",
        })

    fig_ring = concentric_ring(
        center_title=f"{eq:,.0f}",
        center_value=f"{pnl_today:+,.0f}",
        caption="Equity • P&L today",
        outer_bipolar=outer,
        outer_cap=1.0,
        middle_mode="split",
        middle_split=(left, right),
        inner_unipolar=exp or 0.0,
        inner_cap=1.0,
        size=(280, 280),
        ticks=ticks,
    )
    st.plotly_chart(fig_ring, use_container_width=True, config={'displayModeBar': False})
except Exception:
    pass

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
            except Exception:
                # Suppress noisy warnings when bridge is down; health strip above indicates status
                continue
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
