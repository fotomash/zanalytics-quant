# File: dashboard/pages/12_🔥_Pulse_Wyckoff_Live.py
"""
Zanalytics Pulse - Live Wyckoff Terminal
Real-time tick analysis with adaptive Wyckoff scoring and behavioral guards
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
import json
import time
import redis
from typing import Dict, List, Tuple, Optional
import os
from dotenv import load_dotenv

# --- Configuration ---
st.set_page_config(
    page_title="Pulse Wyckoff Live Terminal",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Secrets/Env with defaults
MT5_API_URL = os.getenv("MT5_API_URL", "http://localhost:8000")
PULSE_API_URL = os.getenv("PULSE_API_URL", "http://localhost:8000/api/pulse")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Starting equity default
STARTING_EQUITY = float(os.getenv("STARTING_EQUITY", 200000))

# Initialize Redis
@st.cache_resource
def init_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        return r
    except:
        st.warning("Redis unavailable - disabling streaming features")
        return None

redis_client = init_redis()

# Health check helper
def check_health(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=1)
        return r.ok
    except Exception:
        return False

# Data Fetching
@st.cache_data(ttl=30)
def fetch_tick_data(symbol: str, limit: int = 5000, use_mock: bool = False, use_redis: bool = False) -> pd.DataFrame:
    """Fetch tick data from MT5 API with retries and mock fallback"""

    def _mock_ticks() -> pd.DataFrame:
        idx = pd.date_range(datetime.utcnow() - timedelta(minutes=limit // 10),
                            periods=limit, freq="6S")
        df_mock = pd.DataFrame({
            "bid": np.random.normal(1.085, 0.001, limit).cumsum(),
            "ask": np.random.normal(1.0852, 0.001, limit).cumsum(),
            "volume": np.random.randint(1, 10, limit)
        }, index=idx)
        df_mock["price"] = (df_mock["bid"] + df_mock["ask"]) / 2
        return df_mock

    if use_mock:
        return _mock_ticks()

    # Prefer Redis live stream if requested and available
    if use_redis and redis_client is not None:
        try:
            # Try common stream keys in order
            stream_keys = [
                f"stream:pulse:ticks:{symbol}",
                f"stream:ticks:{symbol}",
                "ticks",
            ]
            stream = next((k for k in stream_keys if redis_client.xlen(k) > 0), None)
            if stream:
                # Get latest entries in reverse to limit, then sort ascending
                entries = redis_client.xrevrange(stream, count=limit)
                rows = []
                for _id, data in entries:
                    # Normalize timestamp
                    ts = data.get('ts') or data.get('timestamp') or data.get('time')
                    try:
                        ts_parsed = pd.to_datetime(ts, utc=True)
                    except Exception:
                        try:
                            ts_num = pd.to_numeric(ts, errors='coerce')
                            unit = 's'
                            if ts_num and ts_num > 1e18:
                                unit = 'ns'
                            elif ts_num and ts_num > 1e12:
                                unit = 'ms'
                            ts_parsed = pd.to_datetime(ts_num, unit=unit, utc=True)
                        except Exception:
                            ts_parsed = pd.NaT
                    bid = float(data.get('bid') or data.get('Bid') or data.get('b', 0) or 0)
                    ask = float(data.get('ask') or data.get('Ask') or data.get('a', 0) or 0)
                    last = data.get('last') or data.get('price')
                    try:
                        last = float(last) if last is not None else None
                    except Exception:
                        last = None
                    vol = data.get('volume') or data.get('vol') or 1
                    try:
                        vol = float(vol)
                    except Exception:
                        vol = 1.0
                    price = last if last is not None else ((bid + ask) / 2 if bid and ask else None)
                    if ts_parsed is not pd.NaT and price is not None:
                        rows.append({'timestamp': ts_parsed, 'bid': bid, 'ask': ask, 'price': price, 'volume': vol})
                if rows:
                    df_live = pd.DataFrame(rows).dropna(subset=['timestamp']).sort_values('timestamp').set_index('timestamp')
                    return df_live.tail(limit)
        except Exception:
            pass

    params = {"symbol": symbol, "limit": limit}
    last_error = None
    for _ in range(3):
        try:
            response = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            if not data:
                st.warning(f"No tick data for {symbol}")
                return _mock_ticks()
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
            df = df.set_index("timestamp").sort_index()
            if "last" in df and df["last"].notna().any():
                df["price"] = df["last"]
            elif "bid" in df and "ask" in df:
                df["price"] = (df["bid"] + df["ask"]) / 2
            if "volume" not in df:
                df["volume"] = 1.0
            return df
        except Exception as e:
            last_error = e
            time.sleep(1)

    st.error(f"MT5 API error: {last_error} - using mock data")
    return _mock_ticks()

def aggregate_to_bars(df: pd.DataFrame, timeframe: str = '1min') -> pd.DataFrame:
    """Aggregate ticks to OHLCV bars with robust handling"""
    if df.empty:
        return pd.DataFrame()
    
    # Use price column for OHLC
    bars = df['price'].resample(timeframe).ohlc()
    bars['volume'] = df['volume'].resample(timeframe).sum()
    bars = bars.dropna(how='all')
    return bars

# Pulse API Integration
def get_pulse_score(bars_df: pd.DataFrame, symbol: str) -> Dict:
    """Get confluence score from Pulse API"""
    if bars_df.empty:
        return {}

    bars_list = []
    for idx, row in bars_df.tail(100).iterrows():
        bars_list.append({
            'ts': idx.isoformat(),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume'])
        })

    try:
        response = requests.post(
            f"{PULSE_API_URL}/wyckoff/score",
            json={'bars': bars_list},
            timeout=2.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Pulse API error: {e}")
        return {}

# Adaptive Wyckoff Analysis (Placeholder for full implementation)
def analyze_wyckoff_adaptive(df: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
    """Adaptive Wyckoff analysis with news buffer"""
    if df.empty:
        return df
    
    # Simplified adaptive features (integrate full wyckoff_adaptive.py)
    win = config.get('window', 50) if config else 50
    df['sma'] = df['close'].rolling(win).mean()
    df['volume_sma'] = df['volume'].rolling(win).mean()
    df['volume_z'] = (df['volume'] - df['volume_sma']) / df['volume'].rolling(win).std().fillna(1)

    phases = []
    for i in range(len(df)):
        if df['volume_z'].iloc[i] > 1.5:
            phases.append('High Activity')
        else:
            phases.append('Normal')
    df['vsa'] = phases

    news_threshold = config.get('news_buffer', {}).get('volz_thresh', 3.0) if config else 3.0
    df['news_event'] = df['volume_z'].abs() > news_threshold

    # Placeholder Wyckoff fields to avoid KeyErrors in the dashboard
    df['phase'] = 'Neutral'
    df['phase_confidence'] = 0.0
    df['spring'] = False
    df['upthrust'] = False

    return df

# MTF Conflict Detection
def detect_mtf_conflict(labels_1m: str, labels_5m: str, labels_15m: str) -> bool:
    """Simple MTF conflict detection"""
    if not all([labels_1m, labels_5m, labels_15m]):
        return False
    bull_htf = labels_5m in ["Markup", "Accumulation"] or labels_15m in ["Markup", "Accumulation"]
    bear_htf = labels_5m in ["Markdown", "Distribution"] or labels_15m in ["Markdown", "Distribution"]
    return (labels_1m == "Distribution" and bull_htf) or (labels_1m == "Accumulation" and bear_htf)

# Equity and drawdown helpers
def compute_equity_curve(df: pd.DataFrame, start_equity: float) -> pd.Series:
    """Convert close prices into a simple equity curve"""
    if df.empty or 'close' not in df:
        return pd.Series(dtype=float)
    returns = df['close'].pct_change().fillna(0)
    equity = (1 + returns).cumprod() * start_equity
    return equity


def calculate_max_drawdown(equity: pd.Series) -> float:
    """Return max drawdown as a negative fraction of peak equity"""
    if equity.empty:
        return 0.0
    cumulative_max = equity.cummax()
    drawdown = (equity - cumulative_max) / cumulative_max
    return float(drawdown.min())

# Dashboard Main
def main():
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Service health indicators
        st.subheader("Service Status")
        api_ok = check_health(MT5_API_URL)
        try:
            redis_ok = bool(redis_client and redis_client.ping())
        except Exception:
            redis_ok = False
        st.write(f"MT5 API: {'🟢' if api_ok else '🔴'}")
        st.write(f"Redis: {'🟢' if redis_ok else '🔴'}")

        # Symbol selection
        symbol = st.selectbox(
            "Symbol",
            ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "DXY"],
            index=0
        )
        
        # Data parameters
        st.subheader("Data Settings")
        tick_limit = st.slider("Number of Ticks", 1000, 20000, 5000, 1000)
        timeframe = st.selectbox(
            "Aggregation Timeframe",
            ["30s", "1min", "5min", "15min", "30min", "1H"],
            index=1
        )
        use_mock = st.checkbox("Use Mock Data", value=False)
        use_redis_stream = st.checkbox("Use Redis Live Stream", value=True, help="Prefer Redis ticks when available")
        
        # Analysis parameters
        st.subheader("Analysis Settings")
        window = st.slider("Analysis Window", 20, 100, 50, 5)
        
        # News buffer
        st.subheader("News Buffer")
        news_enabled = st.checkbox("Enable News Detection", value=True)
        news_threshold = st.slider("News Threshold (Z-score)", 2.0, 5.0, 3.0, 0.5)
        
        # Auto-refresh
        st.subheader("Real-time Settings")
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
        show_redis_stream = st.checkbox("Show Redis Stream", value=False)

        # Risk settings
        st.subheader("Risk Settings")
        starting_equity = st.number_input("Starting Equity", value=STARTING_EQUITY, step=100.0)
        daily_risk_pct = st.slider("Daily Risk %", 0.1, 10.0, 3.0, 0.1)
        anticipated_positions = st.slider("Anticipated Positions", 1, 20, 5, 1)

    # Main content
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    # Fetch tick data
    with st.spinner(f"Fetching {tick_limit} ticks for {symbol}..."):
        tick_df = fetch_tick_data(symbol, tick_limit, use_mock, use_redis_stream)
    
    if not tick_df.empty:
        st.success(f"Fetched {len(tick_df)} ticks | Time range: {tick_df.index.min()} to {tick_df.index.max()}")
        
        # Aggregate to bars
        bars_df = aggregate_to_bars(tick_df, timeframe)
        
        # Prepare config
        config = {
            'window': window,
            'news_buffer': {
                'enabled': news_enabled,
                'volz_thresh': news_threshold
            }
        }
        
        # Run adaptive analysis
        analyzed_df = analyze_wyckoff_adaptive(bars_df, config)
        
        # Get Pulse score
        pulse_score = get_pulse_score(analyzed_df, symbol)
        
        # MTF analysis (resample and score)
        mtf_scores = {}
        for tf in ['1min', '5min', '15min']:
            mtf_bars = aggregate_to_bars(tick_df, tf)
            if not mtf_bars.empty:
                mtf_scores[tf] = get_pulse_score(mtf_bars, symbol)
        
        # MTF conflict detection
        labels_1m = mtf_scores.get('1min', {}).get('phase', 'Neutral')
        labels_5m = mtf_scores.get('5min', {}).get('phase', 'Neutral')
        labels_15m = mtf_scores.get('15min', {}).get('phase', 'Neutral')
        mtf_conflict = detect_mtf_conflict(labels_1m, labels_5m, labels_15m)

        # Risk calculations
        max_loss_today = starting_equity * (daily_risk_pct / 100.0)
        max_loss_per_trade = max_loss_today / max(anticipated_positions, 1)
        equity_curve = compute_equity_curve(analyzed_df, starting_equity)
        max_drawdown = calculate_max_drawdown(equity_curve)
        
        # Display key metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Phase", analyzed_df['phase'].iloc[-1] if 'phase' in analyzed_df.columns else 'Unknown')
        
        with col2:
            confidence = analyzed_df['phase_confidence'].iloc[-1] if 'phase_confidence' in analyzed_df.columns else 0
            st.metric("Confidence", f"{confidence:.2%}")
        
        with col3:
            st.metric("Pulse Score", f"{pulse_score.get('score', 0)}/100")
        
        with col4:
            springs = analyzed_df['spring'].sum() if 'spring' in analyzed_df.columns else 0
            st.metric("Springs", springs)
        
        with col5:
            news_events = analyzed_df['news_event'].sum() if 'news_event' in analyzed_df.columns else 0
            st.metric("News Events", news_events)
        
        with col6:
            st.metric("MTF Conflict", "Yes" if mtf_conflict else "No")

        # Risk metrics
        risk_col1, risk_col2, risk_col3 = st.columns(3)
        with risk_col1:
            st.metric("Max Drawdown", f"{abs(max_drawdown)*100:.2f}%")
        with risk_col2:
            st.metric("Max Loss Today", f"{max_loss_today:,.2f}")
        with risk_col3:
            st.metric("Max Loss/Trade", f"{max_loss_per_trade:,.2f}")
        
        # Create main chart
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=analyzed_df.index,
            open=analyzed_df['open'], high=analyzed_df['high'],
            low=analyzed_df['low'], close=analyzed_df['close'],
            name="Price"
        ), row=1, col=1)
        
        # Phase backgrounds
        phase_colors = {'Accumulation': 'rgba(0, 255, 0, 0.2)', 'Distribution': 'rgba(255, 0, 0, 0.2)',
                        'Markup': 'rgba(0, 100, 255, 0.2)', 'Markdown': 'rgba(255, 165, 0, 0.2)',
                        'Neutral': 'rgba(128, 128, 128, 0.1)'}
        
        current_phase = None
        phase_start = None
        
        for i, (idx, row) in enumerate(analyzed_df.iterrows()):
            if row['phase'] != current_phase:
                if current_phase is not None and phase_start is not None:
                    fig.add_vrect(
                        x0=phase_start,
                        x1=idx,
                        fillcolor=phase_colors.get(current_phase, 'rgba(128, 128, 128, 0.1)'),
                        layer="below",
                        line_width=0,
                        row=1, col=1
                    )
                current_phase = row['phase']
                phase_start = idx
        
        # Add last phase
        if current_phase is not None and phase_start is not None:
            fig.add_vrect(
                x0=phase_start,
                x1=analyzed_df.index[-1],
                fillcolor=phase_colors.get(current_phase, 'rgba(128, 128, 128, 0.1)'),
                layer="below",
                line_width=0,
                row=1, col=1
            )
        
        # Events
        events = {
            'spring': ('triangle-up', 'green', 'Spring'),
            'upthrust': ('triangle-down', 'red', 'Upthrust')
        }
        
        for event_type, (symbol_shape, color, name) in events.items():
            event_df = analyzed_df[analyzed_df[event_type] == True]
            if not event_df.empty:
                y_values = event_df['low'] - 0.0001 if event_type == 'spring' else event_df['high'] + 0.0001
                fig.add_trace(go.Scatter(
                    x=event_df.index,
                    y=y_values,
                    mode='markers',
                    marker=dict(symbol=symbol_shape, color=color, size=12),
                    name=name,
                    showlegend=True
                ), row=1, col=1)
        
        # News events
        news_df = analyzed_df[analyzed_df['news_event'] == True]
        if not news_df.empty:
            fig.add_trace(go.Scatter(
                x=news_df.index,
                y=news_df['high'] + 0.0002,
                mode='markers',
                marker=dict(symbol='star', color='yellow', size=10, line=dict(color='orange', width=1)),
                name='News Event',
                showlegend=True
            ), row=1, col=1)
        
        # Volume
        fig.add_trace(go.Bar(
            x=analyzed_df.index,
            y=analyzed_df['volume'],
            name="Volume",
            marker_color='gray'
        ), row=2, col=1)
        
        fig.update_layout(
            height=700,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display data tables
        st.markdown("---")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Latest Bars", "🎯 Wyckoff Events", "🚩 VSA Flags", "🔍 Pulse Analysis", "📡 Redis Stream"])

        with tab1:
            st.subheader("Latest Price Bars")
            display_cols = ['open', 'high', 'low', 'close', 'volume', 'phase']
            display_df = analyzed_df[display_cols].tail(20)
            st.dataframe(display_df, use_container_width=True)

        with tab2:
            st.subheader("Detected Wyckoff Events")
            events_df = analyzed_df[(analyzed_df['spring'] == True) |
                                   (analyzed_df['upthrust'] == True)]
            if not events_df.empty:
                event_display = events_df[['close', 'volume', 'phase', 'spring', 'upthrust']]
                st.dataframe(event_display, use_container_width=True)
            else:
                st.info("No Wyckoff events detected in current data")

        with tab3:
            st.subheader("VSA Flags")
            vsa_df = analyzed_df[analyzed_df['vsa'] != 'Normal'] if 'vsa' in analyzed_df.columns else pd.DataFrame()
            if not vsa_df.empty:
                st.dataframe(vsa_df[['open', 'high', 'low', 'close', 'volume', 'volume_z', 'vsa']], use_container_width=True)
            else:
                st.info("No VSA flags triggered")

        with tab4:
            st.subheader("Pulse System Analysis")
            st.json({
                'score': pulse_score.get('score', 0),
                'reasons': pulse_score.get('reasons', []),
                'last_label': pulse_score.get('last_label', 'Unknown'),
                'news_mask': pulse_score.get('news_mask', [])[:10] if pulse_score.get('news_mask') else []
            })

        with tab5:
            if show_redis_stream and redis_client:
                st.subheader("Redis Stream Messages")
                try:
                    # Read last 10 messages from stream
                    messages = redis_client.xread(
                        {f'stream:pulse:signals:{symbol}': '0'},
                        count=10,
                        block=100
                    )
                    if messages:
                        for stream, stream_messages in messages:
                            for msg_id, data in stream_messages:
                                st.json({'id': msg_id, 'data': data})
                    else:
                        st.info("No messages in stream")
                except Exception as e:
                    st.error(f"Redis error: {e}")
            else:
                st.info("Enable 'Show Redis Stream' in settings to view real-time messages")
                
    else:
        st.warning("No tick data received. Please check:")
        st.markdown("""
        1. MT5 terminal is running and connected
        2. Symbol is available in your MT5 account
        3. Market is open for the selected symbol
        4. API service is properly configured
        """)

# Run the dashboard
if __name__ == "__main__":
    main()
