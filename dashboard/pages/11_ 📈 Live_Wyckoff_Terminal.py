# File: dashboard/pages/11_ 📈 Live_Wyckoff_Terminal.py

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime
import time

# --- Page setup ---
st.set_page_config(page_title="Live Wyckoff Terminal", page_icon="📈", layout="wide")
st.title("📈 Live Wyckoff Terminal")
st.caption("Real-time Wyckoff scoring (adaptive + news-aware) from live MT5 ticks")

# --- Service endpoints (adjust hostnames/ports if needed) ---
MT5_API_URL   = st.secrets.get("MT5_API_URL",   "http://mt5:8000")          # e.g., docker service name
PULSE_API_URL = st.secrets.get("PULSE_API_URL", "http://django:8000")       # Django app host

# --- Sidebar controls ---
with st.sidebar:
    st.header("Controls")
    symbol      = st.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"], index=0)
    tick_count  = st.slider("Ticks to fetch", 2000, 30000, 8000, 1000)
    timeframe   = st.selectbox("Primary TF", ["1Min", "5Min", "15Min"], index=0)
    auto_refresh = st.toggle("Auto-refresh (30s)", value=True)

# --- Helpers ---
def _to_mid(df: pd.DataFrame) -> pd.Series:
    # prefer last if valid, else mid of bid/ask, else forward-fill
    if "last" in df and df["last"].notna().any():
        s = df["last"].copy()
        # for instruments with sparse 'last', fill from mid
        if {"bid", "ask"} <= set(df.columns):
            mid = (df["bid"] + df["ask"]) / 2.0
            s = s.fillna(mid)
        return s.ffill()
    if {"bid", "ask"} <= set(df.columns):
        return ((df["bid"] + df["ask"]) / 2.0).ffill()
    # Fallback if only one price field is present
    for c in ["bid", "ask", "price"]:
        if c in df:
            return df[c].ffill()
    return pd.Series(index=df.index, dtype="float64")

def _tick_vol(df: pd.DataFrame) -> pd.Series:
    # MT5 FX often lacks true volume; fallback to tick count
    if "volume" in df and df["volume"].notna().any():
        return df["volume"].fillna(0)
    return pd.Series(1.0, index=df.index)

@st.cache_data(ttl=15, show_spinner=False)
def fetch_ticks(symbol: str, count: int) -> pd.DataFrame:
    try:
        r = requests.get(f"{MT5_API_URL}/ticks", params={"symbol": symbol, "count": count}, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # Expect MT5 'time' as epoch seconds; adapt if endpoint returns ISO8601
        if "time" in df and np.issubdtype(pd.Series(df["time"]).dtype, np.number):
            df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        else:
            df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
        df = df.set_index("time").sort_index()
        return df
    except Exception as e:
        st.error(f"MT5 /ticks error: {e}")
        return pd.DataFrame()

def resample_ticks(df: pd.DataFrame, tf: str = "1Min") -> pd.DataFrame:
    if df.empty:
        return df
    price = _to_mid(df).rename("px")
    vol   = _tick_vol(df).rename("tick_vol")
    agg = pd.concat([price, vol], axis=1)
    bars = pd.DataFrame({
        "open": agg["px"].resample(tf).first(),
        "high": agg["px"].resample(tf).max(),
        "low" : agg["px"].resample(tf).min(),
        "close": agg["px"].resample(tf).last(),
        "volume": agg["tick_vol"].resample(tf).sum()
    }).dropna()
    return bars

def score_bars(bars: pd.DataFrame) -> dict:
    """
    Calls Pulse Wyckoff scorer API:
      POST /api/pulse/wyckoff/score  { "bars": [ {ts,open,high,low,close,volume}, ... ] }
    Returns dict: {score, probs, events, explain}
    """
    if bars.empty:
        return {}
    payload = {"bars": [
        {"ts": ts.isoformat(), "open": float(r.open), "high": float(r.high),
         "low": float(r.low), "close": float(r.close), "volume": float(r.volume)}
        for ts, r in bars.iterrows()
    ]}
    r = requests.post(f"{PULSE_API_URL}/api/pulse/wyckoff/score", json=payload, timeout=5)
    r.raise_for_status()
    return r.json()

def score_mtf(bars_1m: pd.DataFrame) -> dict:
    """Score 1m/5m/15m for conflict display."""
    out = {}
    tf_map = {"1m": "1Min", "5m": "5Min", "15m": "15Min"}
    for name, tf in tf_map.items():
        b = bars_1m if tf == "1Min" else resample_ticks(pd.DataFrame({"mid": bars_1m["close"]}).rename(columns={"mid":"last"}).assign(volume=1.0).set_index(bars_1m.index), tf=tf)
        try:
            out[name] = score_bars(b)
        except Exception:
            out[name] = {}
    return out

# --- Fetch → Resample → Score ---
ticks = fetch_ticks(symbol, tick_count)
if ticks.empty:
    st.info(f"No live ticks yet for {symbol}.")
else:
    bars_1m = resample_ticks(ticks, "1Min")
    bars_pm = resample_ticks(ticks, timeframe)    # primary view
    try:
        score_resp = score_bars(bars_pm)
    except Exception as e:
        st.error(f"Scoring error: {e}")
        score_resp = {}

    # Optional: simple MTF conflict badge
    mtf = score_mtf(bars_1m)
    def _label_from_probs(resp):
        try:
            import numpy as np
            phases = ["Accumulation", "Markup", "Distribution", "Markdown"]
            p = np.array(resp["probs"][-1])
            return phases[int(np.argmax(p))]
        except Exception:
            return "Unknown"
    lbl_1 = _label_from_probs(mtf.get("1m", {}))
    lbl_5 = _label_from_probs(mtf.get("5m", {}))
    lbl_15= _label_from_probs(mtf.get("15m", {}))
    conflict = (lbl_1 in ["Accumulation","Distribution"]) and (lbl_5 in ["Markup","Markdown"] or lbl_15 in ["Markup","Markdown"])

    # --- Chart ---
    st.subheader(f"{symbol} — {timeframe} Candles")
    fig = go.Figure(data=[go.Candlestick(
        x=bars_pm.index, open=bars_pm["open"], high=bars_pm["high"],
        low=bars_pm["low"], close=bars_pm["close"], name="OHLC"
    )])
    fig.update_layout(height=580, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Score & reasons ---
    colA, colB, colC = st.columns([1, 1, 1])
    with colA:
        st.metric("Wyckoff Score (0–100)", f'{score_resp.get("score", 0):.1f}')
        if conflict:
            st.error("MTF conflict detected (1m vs 5m/15m)")
    with colB:
        probs = score_resp.get("probs")
        if probs:
            p_last = probs[-1]
            phases = ["Accumulation", "Markup", "Distribution", "Markdown"]
            st.write("**Phase probabilities (last bar)**")
            st.dataframe(pd.DataFrame({"phase": phases, "p": p_last}))
    with colC:
        explain = score_resp.get("explain", {})
        st.write("**Explain (last bar)**")
        st.json(explain)

    # --- Events table (last 50 flags) ---
    ev = score_resp.get("events", {})
    if ev:
        st.subheader("Events (last 50)")
        ev_df = pd.DataFrame({k: pd.Series(v[-50:]) for k, v in ev.items()})
        st.dataframe(ev_df.tail(20))

# --- Auto-refresh ---
if auto_refresh:
    time.sleep(30)
    st.rerun()
