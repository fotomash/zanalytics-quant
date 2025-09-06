#!/usr/bin/env python3
"""
ZANFLOW Live Trading Dashboard
Real-time market data visualization from mm20.local
"""

import streamlit as st

# Set page config FIRST
st.set_page_config(
    page_title="ZANFLOW Live Trading",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta
import time f
import base64
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# --- Utility Function for Background Image ---
def get_image_as_base64(path):
    """Reads an image file and returns its base64 encoded string."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        return None

class LiveDataConnector:
    """Connect to mm20.local API for live enriched data"""

    def __init__(self, api_url="http://mm20.local:8080"):
        self.api_url = api_url
        self.connection_status = self._test_connection()

    def _test_connection(self):
        """Test API connection"""
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def get_symbols(self):
        """Get all available symbols"""
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def get_live_data(self, symbol):
        """Get live enriched data for a symbol"""
        try:
            response = requests.get(f"{self.api_url}/data/{symbol}", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

class LiveTradingDashboard:
    def __init__(self):
        self.connector = LiveDataConnector()

        # Initialize session state
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = None
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 5
        # Tick data initialization
        if 'tick_data' not in st.session_state:
            st.session_state.tick_data = pd.DataFrame(columns=['time', 'price'])

    def apply_styling(self):
        """Apply the same styling as Home.py"""
        img_base64 = get_image_as_base64("image_af247b.jpg")

        if img_base64:
            st.markdown(f"""
            <style>
            [data-testid="stAppViewContainer"] > .main {{
                background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url(data:image/jpeg;base64,{img_base64});
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}

            /* Sidebar styling */
            section[data-testid="stSidebar"] {{
                background-color: rgba(0,0,0,0.8) !important;
                box-shadow: none !important;
            }}

            /* Panel background */
            .main .block-container {{
                background-color: rgba(0,0,0,0.025) !important;
            }}

            /* Metric styling */
            [data-testid="metric-container"] {{
                background-color: rgba(26,34,45,0.85);
                border: 1px solid rgba(37,48,71,0.4);
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }}
            </style>
            """, unsafe_allow_html=True)

    def create_header(self):
        """Create the header with ZANFLOW branding"""
        st.markdown(
            """
            <div style='
                margin: 0 auto 1.1rem auto;
                max-width: 100%;
                width: 100%;
                text-align: center;
                padding: 0.2em 0 0.1em 0;
                background: linear-gradient(to right, rgba(103,116,255,0.15), rgba(176,66,255,0.15));
                border-radius: 12px;
                border: 2px solid rgba(251,213,1,0.4);
                box-shadow: 0 2px 12px rgba(103,116,255,0.10);
            '>
                <span style='
                    font-family: "Segoe UI", "Montserrat", "Inter", "Arial", sans-serif;
                    font-size: 2.1rem;
                    font-weight: 800;
                    color: #fff;
                    letter-spacing: 0.02em;
                    display: block;
                    margin-bottom: 0.13em;
                    text-transform: uppercase;
                '>
                    ZANFLOW LIVE
                </span>
                <span style='
                    font-family: "Segoe UI", "Montserrat", "Inter", "Arial", sans-serif;
                    font-size: 1.12rem;
                    color: #eee;
                    font-weight: 600;
                    display: block;
                    margin-bottom: 0.19em;
                '>
                    Real-Time Market Data from mm20.local
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    def create_sidebar(self):
        """Create sidebar with symbol selection and controls"""
        st.sidebar.markdown("### 🔴 Live Data Control")

        # Connection status
        if self.connector.connection_status:
            st.sidebar.success("✅ Connected to mm20.local")
        else:
            st.sidebar.error("❌ Cannot connect to mm20.local:8080")
            st.sidebar.info("Make sure the API server is running")
            return False

        # Symbol selection
        symbols = self.connector.get_symbols()
        if symbols:
            selected = st.sidebar.selectbox(
                "Select Symbol",
                options=symbols,
                index=0 if st.session_state.selected_symbol is None else
                      symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in symbols else 0
            )
            st.session_state.selected_symbol = selected
        else:
            st.sidebar.warning("No symbols available")
            return False

        # Refresh controls
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⚡ Refresh Settings")

        st.session_state.auto_refresh = st.sidebar.checkbox(
            "Auto-refresh",
            value=st.session_state.auto_refresh
        )

        if st.session_state.auto_refresh:
            st.session_state.refresh_interval = st.sidebar.slider(
                "Refresh interval (seconds)",
                min_value=1,
                max_value=30,
                value=st.session_state.refresh_interval
            )

        if st.sidebar.button("🔄 Refresh Now"):
            st.rerun()

        return True

    def create_live_chart(self, symbol, live_data):
        """Create main candlestick chart with live data overlay"""

        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=[
                f"{symbol} - Live Price Action",
                "Volume",
                "RSI & Stochastic",
                "MACD"
            ],
            vertical_spacing=0.05,
            row_heights=[0.5, 0.15, 0.15, 0.15],
            shared_xaxes=True
        )

        # Since we only have live tick data, create a simple price line
        # In real implementation, you'd fetch historical data too
        current_time = pd.Timestamp.now()

        if live_data and 'indicators' in live_data:
            indicators = live_data['indicators']
            bid = float(live_data.get('bid', 0))
            ask = float(live_data.get('ask', 0))
            mid_price = (bid + ask) / 2

            # Price markers
            fig.add_trace(go.Scatter(
                x=[current_time],
                y=[bid],
                mode='markers+text',
                name='Bid',
                text=[f"Bid: {bid:.5f}"],
                textposition="bottom center",
                marker=dict(size=15, color='limegreen', symbol='triangle-up'),
                showlegend=True
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=[current_time],
                y=[ask],
                mode='markers+text',
                name='Ask',
                text=[f"Ask: {ask:.5f}"],
                textposition="top center",
                marker=dict(size=15, color='crimson', symbol='triangle-down'),
                showlegend=True
            ), row=1, col=1)

            # Add moving averages as horizontal lines
            ma_colors = {
                'ema_8': '#ff6b6b',
                'ema_21': '#4ecdc4',
                'ema_55': '#45b7d1',
                'sma_200': '#96ceb4'
            }

            for ma, color in ma_colors.items():
                if ma in indicators:
                    value = float(indicators[ma])
                    fig.add_hline(
                        y=value,
                        line_color=color,
                        line_width=2,
                        line_dash="dash",
                        annotation_text=f"{ma.upper()}: {value:.5f}",
                        annotation_position="right",
                        row=1, col=1
                    )

            # Bollinger Bands
            if all(k in indicators for k in ['bb_upper', 'bb_middle', 'bb_lower']):
                bb_upper = float(indicators['bb_upper'])
                bb_lower = float(indicators['bb_lower'])
                bb_middle = float(indicators['bb_middle'])

                # Add BB as horizontal lines
                fig.add_hline(y=bb_upper, line_color='gray', line_width=1, line_dash='dot', row=1, col=1)
                fig.add_hline(y=bb_lower, line_color='gray', line_width=1, line_dash='dot', row=1, col=1)
                fig.add_hline(y=bb_middle, line_color='orange', line_width=1, row=1, col=1)

            # Volume (tick volume)
            if 'volume' in indicators:
                vol = float(indicators['volume'])
                fig.add_trace(go.Bar(
                    x=[current_time],
                    y=[vol],
                    name='Volume',
                    marker_color='yellow',
                    opacity=0.7,
                    width=60000 * 30  # 30 seconds width
                ), row=2, col=1)

            # RSI
            if 'rsi' in indicators:
                rsi = float(indicators['rsi'])
                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[rsi],
                    mode='markers+text',
                    name='RSI',
                    text=[f"{rsi:.1f}"],
                    textposition="top center",
                    marker=dict(size=12, color='#9b59b6'),
                    showlegend=False
                ), row=3, col=1)

                # RSI levels
                fig.add_hline(y=70, line_color="red", line_width=1, line_dash="dash", row=3, col=1)
                fig.add_hline(y=30, line_color="green", line_width=1, line_dash="dash", row=3, col=1)

            # Stochastic
            if 'stoch_k' in indicators and 'stoch_d' in indicators:
                stoch_k = float(indicators['stoch_k'])
                stoch_d = float(indicators['stoch_d'])

                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[stoch_k],
                    mode='markers',
                    name='Stoch K',
                    marker=dict(size=10, color='cyan'),
                    showlegend=False
                ), row=3, col=1)

                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[stoch_d],
                    mode='markers',
                    name='Stoch D',
                    marker=dict(size=10, color='orange'),
                    showlegend=False
                ), row=3, col=1)

            # MACD
            if all(k in indicators for k in ['macd', 'macd_signal', 'macd_histogram']):
                macd = float(indicators['macd'])
                signal = float(indicators['macd_signal'])
                histogram = float(indicators['macd_histogram'])

                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[macd],
                    mode='markers',
                    name='MACD',
                    marker=dict(size=10, color='#3498db'),
                    showlegend=False
                ), row=4, col=1)

                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[signal],
                    mode='markers',
                    name='Signal',
                    marker=dict(size=10, color='#e74c3c'),
                    showlegend=False
                ), row=4, col=1)

                fig.add_trace(go.Bar(
                    x=[current_time],
                    y=[histogram],
                    name='Histogram',
                    marker_color='green' if histogram > 0 else 'red',
                    opacity=0.6,
                    width=60000 * 30
                ), row=4, col=1)

        # Update layout with dark theme
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0.02)",
            plot_bgcolor="rgba(0,0,0,0.02)",
            font=dict(color="white", size=12),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0.8)",
                bordercolor="gray",
                borderwidth=1
            ),
            margin=dict(l=50, r=50, t=100, b=50),
            height=800,
            hovermode='x unified'
        )

        # Update axes
        for i in range(1, 5):
            fig.update_xaxes(
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=False,
                showline=True,
                linecolor="gray",
                linewidth=1,
                row=i, col=1
            )
            fig.update_yaxes(
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=False,
                showline=True,
                linecolor="gray",
                linewidth=1,
                row=i, col=1
            )

        return fig

    def create_metrics_display(self, live_data):
        """Create metrics display similar to Home.py"""
        if not live_data or 'indicators' not in live_data:
            st.warning("No live data available")
            return

        indicators = live_data['indicators']

        # Main metrics
        st.markdown("### 📊 Live Market Metrics")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Bid", f"{live_data.get('bid', 0):.5f}")

        with col2:
            st.metric("Ask", f"{live_data.get('ask', 0):.5f}")

        with col3:
            spread = live_data.get('spread', 0)
            st.metric("Spread", f"{spread}")

        with col4:
            trend = indicators.get('trend', 'NEUTRAL')
            trend_emoji = {
                'STRONG_UP': '🚀',
                'UP': '📈',
                'NEUTRAL': '➡️',
                'DOWN': '📉',
                'STRONG_DOWN': '💥'
            }
            st.metric("Trend", f"{trend_emoji.get(trend, '')} {trend}")

        with col5:
            momentum = indicators.get('momentum', 'NEUTRAL')
            momentum_color = {
                'OVERBOUGHT': '🔴',
                'BULLISH': '🟢',
                'NEUTRAL': '⚪',
                'BEARISH': '🔴',
                'OVERSOLD': '🟢'
            }
            st.metric("Momentum", f"{momentum_color.get(momentum, '')} {momentum}")

        # Detailed indicators in expandable section
        with st.expander("📈 All Indicators", expanded=True):
            # Create 4 columns for indicators
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("**Moving Averages**")
                st.text(f"EMA 8: {indicators.get('ema_8', 'N/A')}")
                st.text(f"EMA 21: {indicators.get('ema_21', 'N/A')}")
                st.text(f"EMA 55: {indicators.get('ema_55', 'N/A')}")
                st.text(f"SMA 200: {indicators.get('sma_200', 'N/A')}")

            with col2:
                st.markdown("**Momentum**")
                rsi = indicators.get('rsi', 50)
                st.text(f"RSI: {rsi:.1f}")
                if rsi > 70:
                    st.error("⚠️ Overbought")
                elif rsi < 30:
                    st.success("⚠️ Oversold")

                st.text(f"Stoch K: {indicators.get('stoch_k', 'N/A')}")
                st.text(f"Stoch D: {indicators.get('stoch_d', 'N/A')}")
                st.text(f"CCI: {indicators.get('cci', 'N/A')}")

            with col3:
                st.markdown("**Volatility**")
                st.text(f"ATR: {indicators.get('atr', 'N/A')}")
                st.text(f"BB Upper: {indicators.get('bb_upper', 'N/A')}")
                st.text(f"BB Lower: {indicators.get('bb_lower', 'N/A')}")
                st.text(f"BB Width: {indicators.get('bb_bandwidth', 'N/A')}%")
                st.text(f"Price in BB: {indicators.get('price_bb_position', 'N/A')}%")

            with col4:
                st.markdown("**Trend Strength**")
                st.text(f"ADX: {indicators.get('adx', 'N/A')}")
                st.text(f"ADX+: {indicators.get('adx_plus', 'N/A')}")
                st.text(f"ADX-: {indicators.get('adx_minus', 'N/A')}")
                st.text(f"MACD: {indicators.get('macd', 'N/A')}")
                st.text(f"Signal: {indicators.get('macd_signal', 'N/A')}")

    def create_mini_charts(self, symbols_data):
        """Create mini charts for multiple symbols like Home.py"""
        st.markdown("### 📊 Multi-Symbol Overview")

        # Create columns for mini charts
        cols = st.columns(min(len(symbols_data), 4))

        for idx, (symbol, data) in enumerate(symbols_data.items()):
            if idx >= 4:  # Limit to 4 charts per row
                break

            with cols[idx]:
                if data and 'indicators' in data:
                    indicators = data['indicators']
                    bid = float(data.get('bid', 0))
                    ask = float(data.get('ask', 0))
                    mid_price = (bid + ask) / 2

                    # Create mini chart
                    fig = go.Figure()

                    # Add price marker
                    fig.add_trace(go.Scatter(
                        x=[0],
                        y=[mid_price],
                        mode='markers',
                        marker=dict(size=20, color='yellow'),
                        showlegend=False
                    ))

                    # Add MA lines as horizontal lines
                    if 'ema_21' in indicators:
                        ema21 = float(indicators['ema_21'])
                        fig.add_hline(y=ema21, line_color='#4ecdc4', line_width=2)

                    # Style
                    fig.update_layout(
                        title=f"{symbol}",
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0.02)",
                        plot_bgcolor="rgba(0,0,0,0.02)",
                        height=200,
                        showlegend=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )

                    fig.update_xaxes(visible=False)
                    fig.update_yaxes(visible=True, gridcolor="rgba(128,128,128,0.2)")

                    st.plotly_chart(fig, use_container_width=True)

                    # Metrics below chart
                    rsi = indicators.get('rsi', 50)
                    trend = indicators.get('trend', 'NEUTRAL')

                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Price", f"{mid_price:.5f}")
                    with metric_col2:
                        st.metric("RSI", f"{rsi:.1f}")

    def run(self):
        """Main dashboard execution"""
        self.apply_styling()
        self.create_header()

        # Create sidebar and check connection
        if not self.create_sidebar():
            st.error("Cannot connect to live data. Please check mm20.local:8080")
            return

        # Get live data for selected symbol
        if st.session_state.selected_symbol:
            live_data = self.connector.get_live_data(st.session_state.selected_symbol)

            # --- Update tick data ---
            if live_data:
                current_tick = {
                    'time': datetime.now(),
                    'price': (float(live_data.get('bid', 0)) + float(live_data.get('ask', 0))) / 2
                }
                st.session_state.tick_data = pd.concat(
                    [st.session_state.tick_data, pd.DataFrame([current_tick])],
                    ignore_index=True
                )
                st.session_state.tick_data = st.session_state.tick_data.tail(1000)

            if live_data:
                # Display live status
                st.markdown(
                    f"<div style='text-align:center; color:#00ff00; font-size:1.2em; margin-bottom:1em;'>"
                    f"● LIVE - {st.session_state.selected_symbol} - Last Update: {datetime.now().strftime('%H:%M:%S')}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # Create main chart
                fig = self.create_live_chart(st.session_state.selected_symbol, live_data)
                st.plotly_chart(fig, use_container_width=True)

                # Display metrics
                self.create_metrics_display(live_data)

                # Display tick chart
                self.create_tick_chart(st.session_state.tick_data)

                # Get data for all symbols for mini charts
                st.markdown("---")
                all_symbols = self.connector.get_symbols()[:4]  # Limit to 4
                symbols_data = {}
                for symbol in all_symbols:
                    if symbol != st.session_state.selected_symbol:
                        data = self.connector.get_live_data(symbol)
                        if data:
                            symbols_data[symbol] = data

                if symbols_data:
                    self.create_mini_charts(symbols_data)
            else:
                st.warning(f"No live data available for {st.session_state.selected_symbol}")

        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(st.session_state.refresh_interval)
            st.rerun()

    def create_tick_chart(self, symbol):ticks = self.connector.get_tick_history(symbol)
        if not ticks:
            st.warning("No tick data available")
            return

        df = pd.DataFrame(ticks)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df['mid_price'] = (df['bid'] + df['ask']) / 2
        df['spread'] = (df['ask'] - df['bid']) * 10000

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                            row_heights=[0.7, 0.3],
                            subplot_titles=["Tick Mid Price", "Spread (pips)"])

        fig.add_trace(go.Scatter(
            x=df['datetime'], y=df['mid_price'],
            mode='lines', name='Mid Price',
            line=dict(color='dodgerblue')
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df['datetime'], y=df['spread'],
            mode='lines', name='Spread',
            line=dict(color='orange')
        ), row=2, col=1)

        fig.update_layout(
            template='plotly_dark',
            height=400,
            margin=dict(l=30, r=30, t=40, b=30),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    dashboard = LiveTradingDashboard()
    dashboard.run()
