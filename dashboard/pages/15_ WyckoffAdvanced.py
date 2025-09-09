```python
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
import requests
import json
import time

# Page Configuration
st.set_page_config(page_title="Enhanced Wyckoff Dashboard", layout="wide", initial_sidebar_state="expanded")

# API Configuration
import os
MT5_API_URL = os.getenv("MT5_API_URL", "http://mt5:5001")

def fetch_tick_data(symbol, count=5000):
    """Fetch raw tick data from MT5 API (GET /ticks)"""
    params = {'symbol': symbol, 'count': count}
    try:
        response = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not data:
            st.warning(f"No ticks for {symbol}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Handle timestamp (from 'time' as UNIX seconds)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df = df.set_index('timestamp').sort_index()
        # Price handling: prefer 'last', else mid of bid/ask
        if 'last' in df and df['last'].notna().any():
            df['price'] = df['last']
        elif 'bid' in df and 'ask' in df:
            df['price'] = (df['bid'] + df['ask']) / 2
        else:
            st.error("No valid price fields")
            return pd.DataFrame()
        
        # Volume: if missing, use 1 per tick
        if 'volume' not in df:
            df['volume'] = 1.0
        return df
    except Exception as e:
        st.error(f"MT5 API error: {e}")
        return pd.DataFrame()

def aggregate_to_bars(df, timeframe='1min'):
    """Aggregate ticks to OHLCV bars"""
    if df.empty:
        return pd.DataFrame()
    
    bars = df['price'].resample(timeframe).ohlc()
    bars['volume'] = df['volume'].resample(timeframe).sum()
    bars = bars.dropna()
    return bars

def analyze_wyckoff_adaptive(df, win=50):
    """
    Adaptive Wyckoff analysis - phases, events, VSA
    This is a simplified version - integrate full wyckoff_adaptive.py for production
    """
    if df.empty or len(df) < win:
        return df
    
    # Adaptive features
    ret = df['close'].pct_change()
    vol_z = (df['volume'] - df['volume'].rolling(win).mean()) / df['volume'].rolling(win).std().fillna(1)
    bb_mid = df['close'].rolling(win).mean()
    bb_sd = df['close'].rolling(win).std()
    bb_lower = bb_mid - 2 * bb_sd
    bb_upper = bb_mid + 2 * bb_sd
    bb_pct = (df['close'] - bb_lower) / (bb_upper - bb_lower + 1e-6)
    
    # Efficiency ratio
    net_change = abs(df['close'].diff(win))
    total_change = df['close'].diff().abs().rolling(win).sum()
    eff_ratio = net_change / (total_change + 1e-6)
    
    # Phase detection
    phases = []
    for i in range(len(df)):
        if bb_pct.iloc[i] < 0.3:
            phases.append('Accumulation')
        elif bb_pct.iloc[i] > 0.7:
            phases.append('Distribution')
        elif ret.iloc[i] > 0:
            phases.append('Markup')
        elif ret.iloc[i] < 0:
            phases.append('Markdown')
        else:
            phases.append('Neutral')
    df['phase'] = phases
    
    # Event detection
    rolling_low = df['low'].rolling(win).min()
    rolling_high = df['high'].rolling(win).max()
    df['spring'] = (df['low'] < rolling_low.shift(1)) & (df['close'] > df['open']) & (vol_z > 0.5)
    df['upthrust'] = (df['high'] > rolling_high.shift(1)) & (df['close'] < df['open']) & (vol_z > 0.5)
    
    # VSA (simplified)
    df['vsa'] = np.where(vol_z > 1.5, 'High Activity', 'Normal')
    
    # News buffer (simplified high vol detection)
    df['news_event'] = vol_z.abs() > 3.0
    
    return df

# Dashboard UI
st.title("Enhanced Wyckoff Dashboard - Live MT5 Ticks")

# Sidebar
with st.sidebar:
    symbol = st.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"], key="wy15_sym")
    tick_count = st.slider("Ticks to Fetch", 1000, 20000, 5000, key="wy15_ticks")
    timeframe = st.selectbox("Timeframe", ["1min", "5min", "15min"], key="wy15_tf")
    auto_refresh = st.toggle("Auto Refresh (30s)", value=True, key="wy15_auto")
    analysis_win = st.slider("Analysis Window", 20, 200, 50, key="wy15_win")

# Fetch & Process
if st.sidebar.button("Fetch Data") or auto_refresh:
    ticks = fetch_tick_data(symbol, tick_count)
    if not ticks.empty:
        bars = aggregate_to_bars(ticks, timeframe)
        
        if len(bars) >= analysis_win:
            analysis_bars = bars.iloc[-analysis_win:]
            analyzed = analyze_wyckoff_adaptive(analysis_bars, analysis_win)
            
            # Display Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Phase", analyzed['phase'].iloc[-1])
            col2.metric("Springs", int(analyzed['spring'].sum()))
            col3.metric("Upthrusts", int(analyzed['upthrust'].sum()))
            col4.metric("News Events", int(analyzed['news_event'].sum()))
            
            # Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            
            # Candlestick
            fig.add_trace(go.Candlestick(x=analyzed.index, open=analyzed['open'], high=analyzed['high'],
                                         low=analyzed['low'], close=analyzed['close']), row=1, col=1)
            
            # Phases (simplified coloring)
            phase_colors = {'Accumulation':'blue', 'Distribution':'red', 'Markup':'green', 'Markdown':'orange', 'Neutral':'gray'}
            for phase, color in phase_colors.items():
                phase_df = analyzed[analyzed['phase'] == phase]
                if not phase_df.empty:
                    fig.add_trace(go.Scatter(x=phase_df.index, y=phase_df['close'], mode='lines',
                                             line=dict(color=color, width=1), name=phase), row=1, col=1)
            
            # Events
            springs = analyzed[analyzed['spring']]
            if not springs.empty:
                fig.add_trace(go.Scatter(x=springs.index, y=springs['low'], mode='markers',
                                         marker=dict(symbol='triangle-up', color='green', size=10), name="Spring"), row=1, col=1)
            
            upthrusts = analyzed[analyzed['upthrust']]
            if not upthrusts.empty:
                fig.add_trace(go.Scatter(x=upthrusts.index, y=upthrusts['high'], mode='markers',
                                         marker=dict(symbol='triangle-down', color='red', size=10), name="Upthrust"), row=1, col=1)
            
            # News
            news = analyzed[analyzed['news_event']]
            if not news.empty:
                fig.add_trace(go.Scatter(x=news.index, y=news['high'], mode='markers',
                                         marker=dict(symbol='star', color='yellow', size=10), name="News Event"), row=1, col=1)
            
            # Volume
            fig.add_trace(go.Bar(x=analyzed.index, y=analyzed['volume'], name="Volume"), row=2, col=1)
            
            fig.update_layout(height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig)
            
            # Data Table
            with st.expander("Analyzed Data"):
                st.dataframe(analyzed)
        else:
            st.warning(f"Insufficient bars ({len(bars)}) for analysis")
    else:
        st.error(f"No ticks fetched for {symbol}")

if auto_refresh:
    time.sleep(30)
    st.experimental_rerun()
