#!/usr/bin/env python3
"""
XAUUSD Professional Trading Dashboard
Ultra-Visual Analysis with 172+ Technical Indicators
Real-time Gold Trading Intelligence
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import warnings
from typing import Dict, List, Optional, Tuple
import math

PARQUET_DATA_DIR = st.secrets["PARQUET_DATA_DIR"]
warnings.filterwarnings('ignore')

# ============================================================================
# BACKGROUND IMAGE SETUP
# ============================================================================
import base64

def get_image_as_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Background image not found at '{path}'")
        return None

img_base64 = get_image_as_base64("theme/image_af247b.jpg")
if img_base64:
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url(data:image/jpeg;base64,{img_base64}) !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
        background-color: transparent !important;
    }}
    body, .block-container {{
        background: none !important;
        background-color: transparent !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# Set main content width to exactly 998px
st.markdown("""
<style>
/* Set main content width to exactly 998px */
.main .block-container {
    max-width: 998px !important;
    padding-left: 1.5vw;
    padding-right: 1.5vw;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

def setup_page():
    """Setup page with professional gold trading theme"""
    # st.set_page_config(
    #     page_title="🥇 XAUUSD Professional Trading Dashboard",
    #     page_icon="🥇",
    #     layout="wide",
    #     initial_sidebar_state="expanded"
    # )

    # Professional Gold Trading CSS
    st.markdown("""
        <style>
        .main {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2d1810 100%);
            color: #ffffff;
        }

        .gold-header {
            background: rgba(255, 165, 0, 0.3);
            padding: 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            /* box-shadow: 0 10px 40px rgba(255, 215, 0, 0.3); */
            color: #000;
            font-weight: bold;
        }

        .metric-gold {
            background: rgba(45, 24, 16, 0.3);
            padding: 1.5rem;
            border-radius: 15px;
            border: 2px solid #FFD700;
            margin: 1rem 0;
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.1);
            text-align: center;
        }

        .signal-box {
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            font-weight: 600;
            text-align: center;
        }

        .buy-signal {
            background: rgba(0, 255, 136, 0.2);
            color: #000;
            /* animation: glow-green 2s infinite; */
            /* box-shadow: 0 0 20px rgba(0, 255, 136, 0.3); */
        }

        .sell-signal {
            background: rgba(255, 68, 68, 0.2);
            color: #fff;
            /* animation: glow-red 2s infinite; */
            /* box-shadow: 0 0 20px rgba(255, 68, 68, 0.3); */
        }

        .neutral-signal {
            background: rgba(255, 170, 0, 0.2);
            color: #000;
        }

        @keyframes glow-green {
            0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.5); }
            50% { box-shadow: 0 0 30px rgba(0, 255, 136, 0.8); }
        }

        @keyframes glow-red {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 68, 68, 0.5); }
            50% { box-shadow: 0 0 30px rgba(255, 68, 68, 0.8); }
        }

        .indicator-card {
            background: rgba(255, 215, 0, 0.1);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
        }

        .price-display {
            font-size: 1.5rem;
            font-weight: bold;
            color: #FFD700;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# DATA LOADING AND PROCESSING
# ============================================================================

@st.cache_data
def load_all_timeframes(selected_pair):
    """Load all timeframe data for selected pair"""
    data_dir = f"{PARQUET_DATA_DIR}{selected_pair}"
    timeframes = {
        '1min': f'{selected_pair}_1min.parquet',
        '5min': f'{selected_pair}_5min.parquet',
        '15min': f'{selected_pair}_15min.parquet',
        '30min': f'{selected_pair}_30min.parquet',
        '1h': f'{selected_pair}_1h.parquet',
        '4h': f'{selected_pair}_4h.parquet',
        '1d': f'{selected_pair}_1d.parquet'
    }

    data = {}
    for tf, filename in timeframes.items():
        try:
            full_path = f"{data_dir}/{filename}"
            df = pd.read_parquet(full_path)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            data[tf] = df
        except Exception as e:
            st.warning(f"Could not load {filename}: {e}")

    return data

def calculate_trading_signals(df):
    """Calculate comprehensive trading signals"""
    signals = {
        'overall_signal': 'NEUTRAL',
        'strength': 0,
        'components': {}
    }

    if df.empty:
        return signals

    latest = df.iloc[-1]

    # RSI Signals
    rsi_14 = latest.get('RSI_14', 50)
    if rsi_14 < 30:
        signals['components']['RSI'] = {'signal': 'BUY', 'strength': 0.8, 'value': rsi_14}
    elif rsi_14 > 70:
        signals['components']['RSI'] = {'signal': 'SELL', 'strength': 0.8, 'value': rsi_14}
    else:
        signals['components']['RSI'] = {'signal': 'NEUTRAL', 'strength': 0.3, 'value': rsi_14}

    # MACD Signals
    macd = latest.get('MACD_12_26_9', 0)
    macd_signal = latest.get('MACD_SIGNAL_12_26_9', 0)
    if macd > macd_signal:
        signals['components']['MACD'] = {'signal': 'BUY', 'strength': 0.7, 'value': macd - macd_signal}
    else:
        signals['components']['MACD'] = {'signal': 'SELL', 'strength': 0.7, 'value': macd - macd_signal}

    # Moving Average Signals
    price = latest.get('close', 0)
    sma_20 = latest.get('SMA_20', 0)
    sma_50 = latest.get('SMA_50', 0)

    if price > sma_20 > sma_50:
        signals['components']['MA_Trend'] = {'signal': 'BUY', 'strength': 0.6, 'value': 'Bullish'}
    elif price < sma_20 < sma_50:
        signals['components']['MA_Trend'] = {'signal': 'SELL', 'strength': 0.6, 'value': 'Bearish'}
    else:
        signals['components']['MA_Trend'] = {'signal': 'NEUTRAL', 'strength': 0.3, 'value': 'Mixed'}

    # Bollinger Bands
    bb_position = latest.get('BB_POSITION_20', 0.5)
    if bb_position < 0.2:
        signals['components']['BB'] = {'signal': 'BUY', 'strength': 0.5, 'value': bb_position}
    elif bb_position > 0.8:
        signals['components']['BB'] = {'signal': 'SELL', 'strength': 0.5, 'value': bb_position}
    else:
        signals['components']['BB'] = {'signal': 'NEUTRAL', 'strength': 0.2, 'value': bb_position}

    # SuperTrend
    supertrend_dir = latest.get('SUPERTREND_DIR_14_2', 0)
    if supertrend_dir > 0:
        signals['components']['SuperTrend'] = {'signal': 'BUY', 'strength': 0.7, 'value': 'Bullish'}
    else:
        signals['components']['SuperTrend'] = {'signal': 'SELL', 'strength': 0.7, 'value': 'Bearish'}

    # Calculate overall signal
    buy_strength = sum([comp['strength'] for comp in signals['components'].values() if comp['signal'] == 'BUY'])
    sell_strength = sum([comp['strength'] for comp in signals['components'].values() if comp['signal'] == 'SELL'])

    if buy_strength > sell_strength + 0.5:
        signals['overall_signal'] = 'BUY'
        signals['strength'] = min(buy_strength / 3.0, 1.0)
    elif sell_strength > buy_strength + 0.5:
        signals['overall_signal'] = 'SELL'
        signals['strength'] = min(sell_strength / 3.0, 1.0)
    else:
        signals['overall_signal'] = 'NEUTRAL'
        signals['strength'] = 0.3

    return signals

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_main_chart(df, timeframe):
    """Create main trading chart with all indicators"""

    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=(
            f'XAUUSD {timeframe.upper()} - Price Action & Indicators',
            'Volume & VWAP',
            'RSI & Stochastic',
            'MACD',
            'SuperTrend & Bollinger Bands'
        ),
        row_heights=[0.4, 0.15, 0.15, 0.15, 0.15]
    )

    # Main candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='XAUUSD',
            increasing_line_color='#FFD700',
            decreasing_line_color='#FF4444',
            increasing_fillcolor='rgba(255, 215, 0, 0.8)',
            decreasing_fillcolor='rgba(255, 68, 68, 0.8)'
        ),
        row=1, col=1
    )

    # Add moving averages
    for ma_period in [20, 50, 200]:
        if f'SMA_{ma_period}' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[f'SMA_{ma_period}'],
                    mode='lines',
                    name=f'SMA {ma_period}',
                    line=dict(width=2),
                    opacity=0.8
                ),
                row=1, col=1
            )

    # Add Bollinger Bands
    if all(col in df.columns for col in ['BB_UPPER_20', 'BB_LOWER_20']):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['BB_UPPER_20'],
                mode='lines',
                name='BB Upper',
                line=dict(color='rgba(255, 255, 255, 0.3)', dash='dot'),
                showlegend=False
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['BB_LOWER_20'],
                mode='lines',
                name='BB Lower',
                line=dict(color='rgba(255, 255, 255, 0.3)', dash='dot'),
                fill='tonexty',
                fillcolor='rgba(255, 215, 0, 0.1)',
                showlegend=False
            ),
            row=1, col=1
        )

    # SuperTrend
    if 'SUPERTREND_14_2' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['SUPERTREND_14_2'],
                mode='lines',
                name='SuperTrend',
                line=dict(color='#00ff88', width=3)
            ),
            row=1, col=1
        )

    # Volume
    if 'volume' in df.columns:
        colors = ['#FFD700' if close >= open_price else '#FF4444'
                 for close, open_price in zip(df['close'], df['open'])]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )

    # VWAP
    if 'vwap_d' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['vwap_d'],
                mode='lines',
                name='VWAP',
                line=dict(color='#ff8800', width=2)
            ),
            row=2, col=1
        )

    # RSI
    if 'RSI_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['RSI_14'],
                mode='lines',
                name='RSI(14)',
                line=dict(color='#9966ff', width=2)
            ),
            row=3, col=1
        )

        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, opacity=0.5)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, opacity=0.5)
        fig.add_hline(y=50, line_dash="dot", line_color="white", row=3, col=1, opacity=0.3)

    # Stochastic
    if all(col in df.columns for col in ['STOCH_K', 'STOCH_D']):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['STOCH_K'],
                mode='lines',
                name='Stoch %K',
                line=dict(color='#00ccff', width=1)
            ),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['STOCH_D'],
                mode='lines',
                name='Stoch %D',
                line=dict(color='#ff6600', width=1)
            ),
            row=3, col=1
        )

    # MACD
    if all(col in df.columns for col in ['MACD_12_26_9', 'MACD_SIGNAL_12_26_9', 'MACD_HIST_12_26_9']):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MACD_12_26_9'],
                mode='lines',
                name='MACD',
                line=dict(color='#00ff88', width=2)
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MACD_SIGNAL_12_26_9'],
                mode='lines',
                name='MACD Signal',
                line=dict(color='#ff4444', width=2)
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['MACD_HIST_12_26_9'],
                name='MACD Histogram',
                marker_color='rgba(255, 255, 255, 0.6)',
                opacity=0.7
            ),
            row=4, col=1
        )

    # ATR (Average True Range)
    if 'ATR_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['ATR_14'],
                mode='lines',
                name='ATR(14)',
                line=dict(color='#ffaa00', width=2)
            ),
            row=5, col=1
        )

    # Update layout
    fig.update_layout(
        title=f'🥇 XAUUSD {timeframe.upper()} - Professional Trading Analysis',
        template='plotly_dark',
        height=1000,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        font=dict(color='white'),
        paper_bgcolor='rgba(10, 10, 10, 0.95)',
        plot_bgcolor='rgba(10, 10, 10, 0.95)'
    )

    # Update y-axes
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="RSI / Stoch", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=4, col=1)
    fig.update_yaxes(title_text="ATR", row=5, col=1)

    return fig

def create_signal_gauge(signal_data):
    """Create signal strength gauge"""
    signal = signal_data['overall_signal']
    strength = signal_data['strength']

    if signal == 'BUY':
        color = '#00ff88'
        value = 50 + (strength * 50)
    elif signal == 'SELL':
        color = '#ff4444'
        value = 50 - (strength * 50)
    else:
        color = '#ffaa00'
        value = 50

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Signal: {signal}"},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 25], 'color': "rgba(255, 68, 68, 0.3)"},
                {'range': [25, 75], 'color': "rgba(255, 170, 0, 0.3)"},
                {'range': [75, 100], 'color': "rgba(0, 255, 136, 0.3)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(
        template='plotly_dark',
        font=dict(color='white', size=16),
        paper_bgcolor='rgba(10, 10, 10, 0.95)',
        height=300
    )

    return fig

def create_indicator_heatmap(df):
    """Create indicator correlation heatmap"""
    # Select key indicators
    indicators = [
        'RSI_14', 'MACD_12_26_9', 'BB_POSITION_20', 'STOCH_K',
        'CCI_14', 'WILLR_14', 'ROC_10', 'MOM_10'
    ]

    available_indicators = [ind for ind in indicators if ind in df.columns]

    if len(available_indicators) < 2:
        return go.Figure()

    corr_matrix = df[available_indicators].corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdYlGn',
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False
    ))

    fig.update_layout(
        title="Indicator Correlation Matrix",
        template='plotly_dark',
        font=dict(color='white'),
        paper_bgcolor='rgba(10, 10, 10, 0.95)',
        height=400
    )

    return fig

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application"""
    setup_page()

    # Header
    st.markdown("""
        <div class="gold-header">
            <h1>📊 Analysis with 172+ Technical Indicators</h1>
            <p>Advanced Multi-Timeframe Analysis • Professional Trading Signals</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Trading Controls")

        # Pair selection
        available_pairs = ['XAUUSD', 'BTCUSD', 'ETHUSD', 'EURUSD', 'GBPUSD']
        selected_pair = st.selectbox(
            "💱 Select Pair",
            options=available_pairs,
            index=0,
            help="Choose trading pair"
        )

        # Timeframe selection will be set after data is loaded
        timeframe_placeholder = st.empty()

        # Analysis options
        st.subheader("🔍 Analysis Options")
        show_signals = st.checkbox("Show Trading Signals", value=True)
        show_correlations = st.checkbox("Show Indicator Correlations", value=True)
        show_all_timeframes = st.checkbox("Multi-Timeframe View", value=False)

        # Risk management
        st.subheader("⚠️ Risk Management")
        risk_percent = st.slider("Risk per Trade (%)", 0.5, 5.0, 2.0, 0.1)
        account_size = st.number_input("Account Size ($)", value=10000, step=1000)

        st.markdown("---")
        st.markdown("**📈 Market Status**")
        st.markdown("🟢 Market Open" if datetime.now().weekday() < 5 else "🔴 Market Closed")

    # Load data
    with st.spinner(f"🔄 Loading {selected_pair} data across all timeframes..."):
        data = load_all_timeframes(selected_pair)

    if not data:
        st.error(f"❌ No data files found. Please ensure {selected_pair} parquet files are available.")
        return

    # Now, put timeframe selection after data is loaded
    available_timeframes = list(data.keys())
    with st.sidebar:
        selected_timeframe = timeframe_placeholder.selectbox(
            "📊 Select Timeframe",
            options=available_timeframes,
            index=len(available_timeframes)-1 if available_timeframes else 0,
            help="Choose timeframe for detailed analysis"
        )

    # Get current timeframe data
    current_df = data[selected_timeframe]

    if current_df.empty:
        st.error(f"❌ No data available for {selected_timeframe}")
        return

    # Calculate signals
    signals = calculate_trading_signals(current_df)

    # Current price and key metrics
    latest = current_df.iloc[-1]
    current_price = latest['close']
    price_change = current_price - current_df.iloc[-2]['close'] if len(current_df) > 1 else 0
    price_change_pct = (price_change / current_df.iloc[-2]['close'] * 100) if len(current_df) > 1 else 0

    # Main metrics display
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
            <div class="metric-gold">
                <div class="price-display">${current_price:.2f}</div>
                <div>Current Gold Price</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        change_color = "#00ff88" if price_change >= 0 else "#ff4444"
        st.markdown(f"""
            <div class="metric-gold">
                <div style="color: {change_color}; font-size: 1.5rem; font-weight: bold;">
                    {price_change:+.2f} ({price_change_pct:+.2f}%)
                </div>
                <div>24h Change</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-gold">
                <div style="font-size: 1.5rem; font-weight: bold;">${latest.get('high', 0):.2f}</div>
                <div>24h High</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="metric-gold">
                <div style="font-size: 1.5rem; font-weight: bold;">${latest.get('low', 0):.2f}</div>
                <div>24h Low</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        volume = latest.get('volume', 0)
        st.markdown(f"""
            <div class="metric-gold">
                <div style="font-size: 1.5rem; font-weight: bold;">{volume:,.0f}</div>
                <div>Volume</div>
            </div>
        """, unsafe_allow_html=True)

    # Trading signals display
    if show_signals:
        st.subheader("🎯 Trading Signals Analysis")

        # Overall signal
        signal_class = f"{signals['overall_signal'].lower()}-signal"
        st.markdown(f"""
            <div class="signal-box {signal_class}">
                <h2>🚨 {signals['overall_signal']} SIGNAL</h2>
                <p>Strength: {signals['strength']:.1%} | Timeframe: {selected_timeframe.upper()}</p>
            </div>
        """, unsafe_allow_html=True)

        # Signal components
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Signal Components")
            for indicator, data in signals['components'].items():
                signal_emoji = "🟢" if data['signal'] == 'BUY' else "🔴" if data['signal'] == 'SELL' else "🟡"
                st.markdown(f"""
                    <div class="indicator-card">
                        <strong>{signal_emoji} {indicator}</strong><br>
                        Signal: {data['signal']} | Strength: {data['strength']:.1%}<br>
                        Value: {data['value']}
                    </div>
                """, unsafe_allow_html=True)

        with col2:
            st.subheader("🎯 Signal Strength Gauge")
            gauge_fig = create_signal_gauge(signals)
            st.plotly_chart(gauge_fig, use_container_width=True)

    # Main chart
    st.subheader(f"📈 {selected_timeframe.upper()} Chart Analysis")
    main_chart = create_main_chart(current_df, selected_timeframe)
    st.plotly_chart(main_chart, use_container_width=True)

    # Multi-timeframe analysis
    if show_all_timeframes:
        st.subheader("🔄 Multi-Timeframe Analysis")

        tf_cols = st.columns(len(data))
        for i, (tf, df) in enumerate(data.items()):
            with tf_cols[i]:
                if isinstance(df, pd.DataFrame) and not df.empty:
                    tf_signals = calculate_trading_signals(df)
                    signal_color = "#00ff88" if tf_signals['overall_signal'] == 'BUY' else "#ff4444" if tf_signals['overall_signal'] == 'SELL' else "#ffaa00"

                    st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; text-align: center; border: 2px solid {signal_color};">
                            <h4>{tf.upper()}</h4>
                            <div style="color: {signal_color}; font-weight: bold; font-size: 1.2rem;">
                                {tf_signals['overall_signal']}
                            </div>
                            <div>Strength: {tf_signals['strength']:.1%}</div>
                            <div>Price: ${df.iloc[-1]['close']:.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)

    # Correlation analysis
    if show_correlations:
        st.subheader("🔗 Indicator Correlation Analysis")
        corr_chart = create_indicator_heatmap(current_df)
        st.plotly_chart(corr_chart, use_container_width=True)

    # Key levels and support/resistance
    st.subheader("🎯 Key Levels Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**📈 Resistance Levels**")
        if 'R1' in latest:
            st.write(f"R3: ${latest.get('R3', 0):.2f}")
            st.write(f"R2: ${latest.get('R2', 0):.2f}")
            st.write(f"R1: ${latest.get('R1', 0):.2f}")

    with col2:
        st.markdown("**⚖️ Pivot Point**")
        if 'PIVOT' in latest:
            st.write(f"**Pivot: ${latest.get('PIVOT', 0):.2f}**")
            st.write(f"Current: ${current_price:.2f}")
            pivot_diff = current_price - latest.get('PIVOT', current_price)
            st.write(f"Diff: {pivot_diff:+.2f}")

    with col3:
        st.markdown("**📉 Support Levels**")
        if 'S1' in latest:
            st.write(f"S1: ${latest.get('S1', 0):.2f}")
            st.write(f"S2: ${latest.get('S2', 0):.2f}")
            st.write(f"S3: ${latest.get('S3', 0):.2f}")

    # Risk calculation
    st.subheader("⚠️ Risk Management Calculator")

    col1, col2, col3 = st.columns(3)

    risk_amount = account_size * (risk_percent / 100)
    atr = latest.get('ATR_14', 10)  # Default ATR if not available
    position_size = risk_amount / atr if atr > 0 else 0

    with col1:
        st.metric("Risk Amount", f"${risk_amount:.2f}")
    with col2:
        st.metric("ATR (14)", f"${atr:.2f}")
    with col3:
        st.metric("Suggested Position Size", f"{position_size:.2f} oz")

    # Technical indicator summary
    with st.expander("📊 Complete Technical Indicator Summary"):
        st.subheader("All Available Indicators")

        # Group indicators by category
        indicator_categories = {
            'Moving Averages': [col for col in current_df.columns if any(x in col for x in ['SMA', 'EMA', 'WMA', 'TEMA', 'TRIMA', 'KAMA', 'MAMA', 'FAMA'])],
            'Oscillators': [col for col in current_df.columns if any(x in col for x in ['RSI', 'STOCH', 'WILLR', 'CCI', 'ROC', 'MOM'])],
            'Volatility': [col for col in current_df.columns if any(x in col for x in ['BB_', 'ATR', 'NATR', 'STDDEV', 'VAR'])],
            'Trend': [col for col in current_df.columns if any(x in col for x in ['MACD', 'SUPERTREND', 'SAR', 'LINEARREG'])],
            'Volume': [col for col in current_df.columns if any(x in col for x in ['volume', 'vwap'])],
            'Japanese': [col for col in current_df.columns if any(x in col for x in ['HA_', 'TENKAN', 'KIJUN', 'SENKOU', 'CHIKOU'])]
        }

        for category, indicators in indicator_categories.items():
            if indicators:
                st.write(f"**{category}:**")
                indicator_data = {}
                for ind in indicators[:10]:  # Limit to first 10 per category
                    value = latest.get(ind, 'N/A')
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        indicator_data[ind] = f"{value:.4f}"
                    else:
                        indicator_data[ind] = str(value)

                # Display in columns
                ind_cols = st.columns(min(3, len(indicator_data)))
                for i, (ind, val) in enumerate(indicator_data.items()):
                    with ind_cols[i % len(ind_cols)]:
                        st.write(f"{ind}: {val}")

                st.write("")  # Add spacing

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #888;">
            <p><strong>🥇 XAUUSD Professional Trading Dashboard</strong></p>
            <p>Real-time analysis with 172+ technical indicators</p>
            <p>⚠️ <em>This is for educational purposes only. Always do your own research before trading.</em></p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
