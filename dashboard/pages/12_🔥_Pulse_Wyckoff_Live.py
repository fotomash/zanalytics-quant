"""
Zanalytics Pulse - Live Wyckoff Terminal
Real-time tick analysis with adaptive Wyckoff scoring and behavioral guards
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
import requests
import json
import redis
from typing import Dict, List, Tuple, Optional
import time

# ==================== Configuration ====================
st.set_page_config(
    page_title="Pulse Wyckoff Live Terminal",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
MT5_API_URL = st.secrets.get("MT5_API_URL", "http://mt5:8000")
PULSE_API_URL = st.secrets.get("PULSE_API_URL", "http://django:8000/api/pulse")
REDIS_HOST = st.secrets.get("REDIS_HOST", "redis")
REDIS_PORT = st.secrets.get("REDIS_PORT", 6379)

# Initialize Redis connection for real-time streaming
@st.cache_resource
def init_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        return r
    except:
        st.warning("Redis not available - running in standalone mode")
        return None

redis_client = init_redis()

# ==================== Data Fetching ====================
@st.cache_data(ttl=5)  # Cache for 5 seconds for near real-time
def fetch_tick_data(symbol: str, limit: int = 1000, 
                   time_after: Optional[str] = None, 
                   time_before: Optional[str] = None) -> pd.DataFrame:
    """Fetch tick data from MT5 API with error handling"""
    params = {
        'symbol': symbol,
        'limit': limit
    }
    if time_after:
        params['time_after'] = time_after
    if time_before:
        params['time_before'] = time_before
    
    try:
        response = requests.get(f"{MT5_API_URL}/ticks", params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                # Handle different timestamp formats
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                elif 'time' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('timestamp', inplace=True)
                return df
    except requests.exceptions.RequestException as e:
        st.error(f"MT5 API Error: {e}")
    
    return pd.DataFrame()

def aggregate_to_bars(df: pd.DataFrame, timeframe: str = '1min') -> pd.DataFrame:
    """Aggregate ticks to OHLCV bars with volume analysis"""
    if df.empty:
        return pd.DataFrame()
    
    # Use bid price for OHLC (can switch to mid-price)
    price_col = 'bid' if 'bid' in df.columns else 'last'
    
    bars = df[price_col].resample(timeframe).ohlc()
    bars['volume'] = df['volume'].resample(timeframe).sum() if 'volume' in df.columns else 0
    
    # Add volume-weighted average price (VWAP)
    if 'volume' in df.columns and df['volume'].sum() > 0:
        bars['vwap'] = (df[price_col] * df['volume']).resample(timeframe).sum() / bars['volume']
    else:
        bars['vwap'] = bars['close']
    
    # Add spread analysis if ask/bid available
    if 'ask' in df.columns and 'bid' in df.columns:
        bars['spread'] = (df['ask'] - df['bid']).resample(timeframe).mean()
        bars['spread_std'] = (df['ask'] - df['bid']).resample(timeframe).std()
    
    bars.dropna(inplace=True)
    return bars

# ==================== Adaptive Wyckoff Analysis ====================
def analyze_wyckoff_adaptive(df: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
    """
    Enhanced Wyckoff analysis with adaptive thresholds and news buffer
    Integrates with the Pulse system's adaptive Wyckoff scorer
    """
    if df.empty or len(df) < 20:
        return df
    
    # Default config if not provided
    if config is None:
        config = {
            'window': 50,
            'vol_gate': 1.2,
            'eff_gate': 0.8,
            'news_buffer': {'enabled': True, 'volz_thresh': 3.0, 'clamp': 0.6}
        }
    
    # Calculate rolling metrics
    window = min(config['window'], len(df))
    df['sma'] = df['close'].rolling(window=window).mean()
    df['volume_sma'] = df['volume'].rolling(window=window).mean()
    
    # Z-score normalization for volume (detect anomalies)
    df['volume_z'] = (df['volume'] - df['volume_sma']) / df['volume'].rolling(window=window).std()
    
    # Price position relative to range
    rolling_min = df['low'].rolling(window=window).min()
    rolling_max = df['high'].rolling(window=window).max()
    df['price_position'] = (df['close'] - rolling_min) / (rolling_max - rolling_min + 1e-6)
    
    # Efficiency ratio (directional movement / total movement)
    net_change = abs(df['close'].diff(window))
    total_change = df['close'].diff().abs().rolling(window=window).sum()
    df['efficiency'] = net_change / (total_change + 1e-6)
    
    # News buffer detection (high volume spikes)
    news_mask = df['volume_z'].abs() > config['news_buffer']['volz_thresh']
    df['news_event'] = news_mask
    
    # Adaptive phase detection
    phases = []
    confidences = []
    
    for i in range(len(df)):
        if i < window:
            phases.append('Insufficient Data')
            confidences.append(0)
            continue
        
        pos = df['price_position'].iloc[i]
        vol_z = df['volume_z'].iloc[i]
        eff = df['efficiency'].iloc[i]
        
        # Apply news buffer clamping
        if df['news_event'].iloc[i] and config['news_buffer']['enabled']:
            confidence = config['news_buffer']['clamp']
        else:
            confidence = 1.0
        
        # Adaptive thresholds based on efficiency
        if eff > config['eff_gate']:  # Strong trend
            if pos < 0.25:
                phases.append('Accumulation')
                confidences.append(0.8 * confidence)
            elif pos > 0.75:
                phases.append('Distribution')
                confidences.append(0.8 * confidence)
            elif df['close'].iloc[i] > df['sma'].iloc[i]:
                phases.append('Markup')
                confidences.append(0.9 * confidence)
            else:
                phases.append('Markdown')
                confidences.append(0.9 * confidence)
        else:  # Ranging/consolidation
            if pos < 0.35 and vol_z > config['vol_gate']:
                phases.append('Accumulation')
                confidences.append(0.7 * confidence)
            elif pos > 0.65 and vol_z > config['vol_gate']:
                phases.append('Distribution')
                confidences.append(0.7 * confidence)
            else:
                phases.append('Trading Range')
                confidences.append(0.5 * confidence)
    
    df['phase'] = phases
    df['phase_confidence'] = confidences
    
    # Wyckoff event detection
    df['spring'] = False
    df['upthrust'] = False
    df['test'] = False
    
    for i in range(window, len(df)):
        # Spring: Break below support with quick recovery on volume
        if (df['low'].iloc[i] < rolling_min.iloc[i-1] and 
            df['close'].iloc[i] > df['open'].iloc[i] and
            df['volume_z'].iloc[i] > 0.5):
            df.loc[df.index[i], 'spring'] = True
        
        # Upthrust: Break above resistance with rejection on volume
        if (df['high'].iloc[i] > rolling_max.iloc[i-1] and 
            df['close'].iloc[i] < df['open'].iloc[i] and
            df['volume_z'].iloc[i] > 0.5):
            df.loc[df.index[i], 'upthrust'] = True
        
        # Test: Low volume retest of support/resistance
        if df['volume_z'].iloc[i] < -0.5:
            if abs(df['low'].iloc[i] - rolling_min.iloc[i-1]) < 0.0001:
                df.loc[df.index[i], 'test'] = True
            elif abs(df['high'].iloc[i] - rolling_max.iloc[i-1]) < 0.0001:
                df.loc[df.index[i], 'test'] = True
    
    return df

# ==================== Pulse Integration ====================
def get_pulse_score(df: pd.DataFrame, symbol: str) -> Dict:
    """Get confluence score from Pulse API"""
    try:
        # Prepare data for API
        bars = df.reset_index().to_dict('records')
        for bar in bars:
            bar['ts'] = bar['timestamp'].isoformat() if 'timestamp' in bar else bar['index'].isoformat()
        
        response = requests.post(
            f"{PULSE_API_URL}/wyckoff/score",
            json={'bars': bars[-100:]},  # Last 100 bars
            timeout=2
        )
        
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    return {'score': 0, 'reasons': ['Pulse API unavailable']}

# ==================== Visualization ====================
def create_wyckoff_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create interactive Wyckoff chart with all indicators"""
    
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.2, 0.15, 0.15],
        subplot_titles=(
            f"{symbol} - Adaptive Wyckoff Analysis",
            "Volume Analysis",
            "Phase Confidence",
            "Efficiency Ratio"
        )
    )
    
    # Main candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="OHLC",
            increasing_line_color='green',
            decreasing_line_color='red'
        ),
        row=1, col=1
    )
    
    # Add SMA
    if 'sma' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['sma'],
                name="SMA",
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )
    
    # Add VWAP
    if 'vwap' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['vwap'],
                name="VWAP",
                line=dict(color='purple', width=1, dash='dash')
            ),
            row=1, col=1
        )
    
    # Phase coloring
    phase_colors = {
        'Accumulation': 'rgba(0, 255, 0, 0.3)',
        'Distribution': 'rgba(255, 0, 0, 0.3)',
        'Markup': 'rgba(0, 100, 255, 0.3)',
        'Markdown': 'rgba(255, 165, 0, 0.3)',
        'Trading Range': 'rgba(128, 128, 128, 0.2)'
    }
    
    # Add phase backgrounds
    current_phase = None
    phase_start = None
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if row['phase'] != current_phase:
            if current_phase and phase_start:
                # Add rectangle for previous phase
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
    
    # Add last phase rectangle
    if current_phase and phase_start:
        fig.add_vrect(
            x0=phase_start,
            x1=df.index[-1],
            fillcolor=phase_colors.get(current_phase, 'rgba(128, 128, 128, 0.1)'),
            layer="below",
            line_width=0,
            row=1, col=1
        )
    
    # Wyckoff Events
    events = {
        'spring': ('triangle-up', 'green', 'Spring'),
        'upthrust': ('triangle-down', 'red', 'Upthrust'),
        'test': ('circle', 'orange', 'Test')
    }
    
    for event_type, (symbol_shape, color, name) in events.items():
        event_df = df[df[event_type] == True]
        if not event_df.empty:
            y_values = event_df['low'] - 0.0001 if event_type == 'spring' else event_df['high'] + 0.0001
            fig.add_trace(
                go.Scatter(
                    x=event_df.index,
                    y=y_values,
                    mode='markers',
                    marker=dict(symbol=symbol_shape, color=color, size=12),
                    name=name,
                    showlegend=True
                ),
                row=1, col=1
            )
    
    # News events
    news_df = df[df['news_event'] == True]
    if not news_df.empty:
        fig.add_trace(
            go.Scatter(
                x=news_df.index,
                y=news_df['high'] + 0.0002,
                mode='markers',
                marker=dict(symbol='star', color='yellow', size=10, line=dict(color='orange', width=1)),
                name='News Event',
                showlegend=True
            ),
            row=1, col=1
        )
    
    # Volume with Z-score coloring
    volume_colors = ['red' if z < -1 else 'green' if z > 1 else 'gray' 
                     for z in df['volume_z']] if 'volume_z' in df.columns else 'gray'
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name="Volume",
            marker_color=volume_colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Phase confidence
    if 'phase_confidence' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['phase_confidence'],
                name="Confidence",
                fill='tozeroy',
                line=dict(color='purple', width=1),
                showlegend=False
            ),
            row=3, col=1
        )
        
        # Add confidence threshold line
        fig.add_hline(y=0.7, line_dash="dash", line_color="red", 
                      annotation_text="Min Confidence", row=3, col=1)
    
    # Efficiency ratio
    if 'efficiency' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['efficiency'],
                name="Efficiency",
                line=dict(color='orange', width=1),
                showlegend=False
            ),
            row=4, col=1
        )
        
        # Add efficiency threshold
        fig.add_hline(y=0.8, line_dash="dash", line_color="green", 
                      annotation_text="Trend", row=4, col=1)
    
    # Update layout
    fig.update_layout(
        height=900,
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
    
    # Update axes
    fig.update_xaxes(title_text="Time", row=4, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Confidence", row=3, col=1, range=[0, 1])
    fig.update_yaxes(title_text="Efficiency", row=4, col=1, range=[0, 1])
    
    return fig

# ==================== Main Dashboard ====================
def main():
    st.title("🔥 Pulse Wyckoff Live Terminal")
    st.markdown("Real-time adaptive Wyckoff analysis with behavioral guards and news detection")
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Symbol selection
        symbol = st.selectbox(
            "Symbol",
            ["EURUSD", "GBPUSD", "USDJPY", "EURGBP", "XAUUSD", "BTCUSD", "SPX500"],
            index=0
        )
        
        # Data parameters
        st.subheader("Data Settings")
        tick_limit = st.slider("Number of Ticks", 500, 10000, 2000, 100)
        timeframe = st.selectbox(
            "Aggregation Timeframe",
            ["1min", "5min", "15min", "30min", "1H"],
            index=0
        )
        
        # Analysis parameters
        st.subheader("Analysis Settings")
        window = st.slider("Analysis Window", 20, 100, 50, 5)
        vol_gate = st.slider("Volume Gate (Z-score)", 0.5, 2.0, 1.2, 0.1)
        eff_gate = st.slider("Efficiency Gate", 0.5, 1.0, 0.8, 0.05)
        
        # News buffer
        st.subheader("News Buffer")
        news_enabled = st.checkbox("Enable News Detection", value=True)
        news_threshold = st.slider("News Threshold (Z-score)", 2.0, 5.0, 3.0, 0.5)
        news_clamp = st.slider("Confidence Clamp", 0.3, 0.8, 0.6, 0.1)
        
        # Auto-refresh
        st.subheader("Real-time Settings")
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
        show_redis_stream = st.checkbox("Show Redis Stream", value=False)
        
        # Action buttons
        st.markdown("---")
        fetch_button = st.button("🔄 Fetch Data", type="primary", use_container_width=True)
        
        # Connection status
        st.markdown("---")
        st.subheader("📡 Connection Status")
        
        # Check MT5 API
        try:
            r = requests.get(f"{MT5_API_URL}/health", timeout=1)
            if r.status_code == 200:
                st.success("✅ MT5 API Connected")
            else:
                st.error("❌ MT5 API Error")
        except:
            st.warning("⚠️ MT5 API Offline")
        
        # Check Pulse API
        try:
            r = requests.get(f"{PULSE_API_URL}/health", timeout=1)
            if r.status_code == 200:
                st.success("✅ Pulse API Connected")
            else:
                st.error("❌ Pulse API Error")
        except:
            st.warning("⚠️ Pulse API Offline")
        
        # Check Redis
        if redis_client:
            st.success("✅ Redis Connected")
        else:
            st.warning("⚠️ Redis Offline")
    
    # Main content area
    if fetch_button or auto_refresh:
        # Fetch tick data
        with st.spinner(f"Fetching {tick_limit} ticks for {symbol}..."):
            tick_df = fetch_tick_data(symbol, tick_limit)
        
        if not tick_df.empty:
            # Show tick statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Ticks Fetched", len(tick_df))
            with col2:
                st.metric("Time Range", f"{(tick_df.index[-1] - tick_df.index[0]).total_seconds()/60:.1f} min")
            with col3:
                if 'bid' in tick_df.columns and 'ask' in tick_df.columns:
                    avg_spread = (tick_df['ask'] - tick_df['bid']).mean()
                    st.metric("Avg Spread", f"{avg_spread*10000:.2f} pips")
            with col4:
                if 'volume' in tick_df.columns:
                    st.metric("Total Volume", f"{tick_df['volume'].sum():,.0f}")
            
            # Aggregate to bars
            bars_df = aggregate_to_bars(tick_df, timeframe)
            
            if not bars_df.empty and len(bars_df) > 20:
                # Prepare config
                config = {
                    'window': window,
                    'vol_gate': vol_gate,
                    'eff_gate': eff_gate,
                    'news_buffer': {
                        'enabled': news_enabled,
                        'volz_thresh': news_threshold,
                        'clamp': news_clamp
                    }
                }
                
                # Run adaptive Wyckoff analysis
                analyzed_df = analyze_wyckoff_adaptive(bars_df, config)
                
                # Get Pulse score
                pulse_score = get_pulse_score(analyzed_df, symbol)
                
                # Display Pulse metrics
                st.markdown("---")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    current_phase = analyzed_df['phase'].iloc[-1] if 'phase' in analyzed_df.columns else 'Unknown'
                    st.metric("Current Phase", current_phase)
                
                with col2:
                    confidence = analyzed_df['phase_confidence'].iloc[-1] if 'phase_confidence' in analyzed_df.columns else 0
                    st.metric("Confidence", f"{confidence:.2%}")
                
                with col3:
                    st.metric("Pulse Score", f"{pulse_score.get('score', 0)}/100")
                
                with col4:
                    springs = analyzed_df['spring'].sum() if 'spring' in analyzed_df.columns else 0
                    st.metric("Springs Detected", springs)
                
                with col5:
                    news_events = analyzed_df['news_event'].sum() if 'news_event' in analyzed_df.columns else 0
                    st.metric("News Events", news_events)
                
                # Display main chart
                st.markdown("---")
                fig = create_wyckoff_chart(analyzed_df, symbol)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display data tables
                st.markdown("---")
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Latest Bars", "📈 Wyckoff Events", "🎯 Pulse Analysis", "📡 Redis Stream"])
                
                with tab1:
                    st.subheader("Latest Price Bars")
                    display_cols = ['open', 'high', 'low', 'close', 'volume', 'phase', 'phase_confidence']
                    display_df = analyzed_df[display_cols].tail(20)
                    st.dataframe(display_df, use_container_width=True)
                
                with tab2:
                    st.subheader("Detected Wyckoff Events")
                    events_df = analyzed_df[(analyzed_df['spring'] == True) | 
                                           (analyzed_df['upthrust'] == True) | 
                                           (analyzed_df['test'] == True)]
                    if not events_df.empty:
                        event_display = events_df[['close', 'volume', 'phase', 'spring', 'upthrust', 'test']]
                        st.dataframe(event_display, use_container_width=True)
                    else:
                        st.info("No Wyckoff events detected in current data")
                
                with tab3:
                    st.subheader("Pulse System Analysis")
                    st.json({
                        'score': pulse_score.get('score', 0),
                        'reasons': pulse_score.get('reasons', []),
                        'last_label': pulse_score.get('last_label', 'Unknown'),
                        'news_mask': pulse_score.get('news_mask', [])[:10] if pulse_score.get('news_mask') else []
                    })
                
                with tab4:
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
                st.warning(f"Not enough bars for analysis. Got {len(bars_df)} bars, need at least 20.")
        else:
            st.error(f"No tick data received for {symbol}. Please check:")
            st.markdown("""
            1. MT5 terminal is running and connected
            2. Symbol is available in your MT5 account
            3. Market is open for the selected symbol
            4. API service is properly configured
            """)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(5)
        st.rerun()

# Run the dashboard
if __name__ == "__main__":
    main()
