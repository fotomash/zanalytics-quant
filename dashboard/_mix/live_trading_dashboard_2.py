#!/usr/bin/env python3
"""
ZANFLOW v12 Ultimate Trading Dashboard with Live Tick Integration
Combines comprehensive analysis with real-time bid/ask tick data
"""

from _dash_v_2.tick_chart import TickChart

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
import warnings
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
import re
import base64
import redis
import time
import requests
warnings.filterwarnings('ignore')

# --- Streamlit page configuration (must be first Streamlit command) ---
st.set_page_config(
    page_title="ZANFLOW v12 Ultimate Live",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Live Data Connector ---
class LiveTickConnector:
    """Enhanced live data connector with Redis and API support"""

    def __init__(self, api_url="http://mm20.local:8080"):
        self.api_url = api_url
        self.redis_client = self._init_redis()
        self._test_connections()

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            return r
        except:
            return None

    def _test_connections(self):
        """Test both Redis and API connections"""
        # Test Redis
        if self.redis_client:
            st.sidebar.success("✅ Redis connected")
        else:
            st.sidebar.warning("⚠️ Redis not connected")

        # Test API
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                st.sidebar.success("✅ Connected to mm20.local")
            else:
                st.sidebar.warning("⚠️ API connected but returned error")
        except Exception:
            st.sidebar.error("❌ Cannot connect to mm20.local:8080")

    def get_live_data(self, symbol="EURUSD"):
        """Get live data from Redis (MT5 format)"""
        if not self.redis_client:
            return None

        try:
            key = f"mt5:{symbol}:latest"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except:
            pass
        return None

    def get_tick_history(self, symbol="EURUSD", limit=100):
        """Get tick history from Redis"""
        if not self.redis_client:
            return []

        try:
            key = f"mt5:{symbol}:history"
            history = self.redis_client.lrange(key, 0, limit-1)
            return [json.loads(h) for h in history]
        except:
            return []

    def get_symbols(self):
        """Get available symbols"""
        if not self.redis_client:
            return ["EURUSD", "GBPUSD", "USDJPY"]  # Default symbols

        try:
            keys = self.redis_client.keys("mt5:*:latest")
            symbols = []
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 2:
                    symbols.append(parts[1])
            return sorted(set(symbols)) if symbols else ["EURUSD", "GBPUSD", "USDJPY"]
        except:
            return ["EURUSD", "GBPUSD", "USDJPY"]

# --- Parquet scanning helper ---
def scan_parquet_files(data_dir):
    """Scan directory for Parquet files, returning (symbol, timeframe, rel_path)"""
    files = []
    for f in Path(data_dir).rglob("*.parquet"):
        name = f.stem.upper()
        parent = f.parent.name.upper()
        # If filename looks like timeframe, parent is symbol
        if re.match(r"\d+[A-Z]+", name):
            symbol = parent
            timeframe = name
        # If folder looks like timeframe, filename is symbol
        elif re.match(r"\d+[A-Z]+", parent):
            symbol = name
            timeframe = parent
        # Fallback: try SYMBOL_TIMEFRAME in filename
        else:
            m = re.match(r"(.*?)_(\d+[a-zA-Z]+)$", name, re.IGNORECASE)
            if m:
                symbol, timeframe = m.group(1).upper(), m.group(2).upper()
            else:
                continue

        files.append((symbol, timeframe, f.relative_to(data_dir)))
    return files

class UltimateZANFLOWDashboard:
    def __init__(self, data_directory=None):
        # Pull path from .streamlit/secrets.toml if not passed
        if data_directory is None:
            data_directory = st.secrets.get("PARQUET_DATA_DIR", "./data")
        self.data_dir = Path(data_directory)
        self.pairs_data = {}
        self.analysis_reports = {}
        self.smc_analysis = {}
        self.wyckoff_analysis = {}
        self.microstructure_data = {}
        # Store latest .txt and .json insights per pair
        self.latest_txt_reports = {}
        self.latest_json_insights = {}
        self.live_connector = LiveTickConnector()
        self.tick_chart = TickChart()

        # Initialize session state for live mode
        if 'live_mode' not in st.session_state:
            st.session_state['live_mode'] = False
        if 'auto_refresh' not in st.session_state:
            st.session_state['auto_refresh'] = True
        if 'refresh_interval' not in st.session_state:
            st.session_state['refresh_interval'] = 2

    def load_all_data(self):
        """Load all processed data silently"""
        # CSV loading logic removed - Parquet only mode
        pass

    def create_main_dashboard(self):
        """Create the ultimate dashboard interface"""

        # --- Match Home.py visual style (background, sidebar, panels) ---
        def get_image_as_base64(path):
            try:
                with open(path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode()
            except Exception:
                return None

        img_base64 = get_image_as_base64("image_af247b.jpg")  # NOT "./pages/..."
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
            </style>
            """, unsafe_allow_html=True)

        # Sidebar (copy from Home.py)
        st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            background-color: rgba(0,0,0,0.8) !important;
            box-shadow: none !important;
        }
        button[kind="secondary"] {
            background-color: #242424 !important;
            color: #fff !important;
            border: 1px solid rgba(250,250,250,0.12) !important;
            font-weight: 600 !important;
            padding: 0.5em 1em !important;
            border-radius: 8px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Panel transparency (copy from Home.py)
        st.markdown("""
        <style>
        .main .block-container {
            background-color: rgba(0,0,0,0.025) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # --- New prominent gold-accented banner (from Home.py) ---
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
                    ZANALYTICS LIVE
                </span>
                <span style='
                    font-family: "Segoe UI", "Montserrat", "Inter", "Arial", sans-serif;
                    font-size: 1.12rem;
                    color: #eee;
                    font-weight: 600;
                    display: block;
                    margin-bottom: 0.19em;
                '>
                    Ultimate Analysis with Live Tick Integration
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Legacy loader kept for backward-compat, but no longer required
        try:
            self.load_all_data()
        except Exception:
            pass  # ignore if loader fails – we now rely on Parquet scanning

        # Sidebar controls
        self.create_sidebar_controls()

        # Main content area
        if st.session_state.get('live_mode', False):
            self.display_live_analysis()
        elif (
            st.session_state.get('selected_pair') and
            st.session_state.get('selected_timeframe') and
            'df_to_use' in st.session_state
        ):
            self.display_ultimate_analysis()
        else:
            # Apply consistent background and style for HOME view
            self.display_market_overview()

    def create_sidebar_controls(self):
        """Create comprehensive sidebar controls"""
        st.sidebar.title("🎛️ Live Analysis Control Center")

        # Live mode toggle
        st.sidebar.markdown("### 🔴 Live Mode")
        col1, col2 = st.sidebar.columns(2)

        if col1.button("▶️ Go Live"):
            st.session_state['live_mode'] = True
            st.rerun()

        if col2.button("⏹️ Stop Live"):
            st.session_state['live_mode'] = False
            st.rerun()

        # Live mode settings
        if st.session_state.get('live_mode', False):
            st.sidebar.success("🔴 LIVE MODE ACTIVE")
            st.session_state['auto_refresh'] = st.sidebar.checkbox("Auto Refresh", True)
            st.session_state['refresh_interval'] = st.sidebar.slider(
                "Refresh Rate (seconds)", 1, 10, 2
            )

            # Available live symbols
            live_symbols = self.live_connector.get_symbols()
            if live_symbols:
                selected_live_symbol = st.sidebar.selectbox(
                    "📡 Live Symbol", live_symbols, key="live_symbol"
                )
                st.session_state['selected_pair'] = selected_live_symbol

                # Manual refresh
                if st.sidebar.button("🔄 Refresh Now"):
                    st.rerun()
            else:
                st.sidebar.warning("No live symbols available")
        else:
            # Static analysis mode
            st.sidebar.info("📊 Static Analysis Mode")

            # Scan Parquet files and extract symbol/timeframe
            file_info = scan_parquet_files(self.data_dir)
            symbols = sorted({sym for sym, _, _ in file_info})
            if not symbols:
                st.sidebar.error("❌ No Parquet files found.")
                return

            selected_pair = st.sidebar.selectbox("📈 Select Symbol", symbols, key="selected_pair")

            available_timeframes = sorted({tf for sym, tf, _ in file_info if sym == selected_pair})
            if not available_timeframes:
                st.sidebar.error("❌ No timeframes found for selected symbol.")
                return

            selected_timeframe = st.sidebar.selectbox("⏱️ Select Timeframe", available_timeframes, key="selected_timeframe")

            # Find the actual Parquet file for symbol+tf
            try:
                rel_path = next(f for sym, tf, f in file_info if sym == selected_pair and tf == selected_timeframe)
            except StopIteration:
                st.sidebar.error("No data found for this symbol/timeframe.")
                return

            full_path = self.data_dir / rel_path
            df = pd.read_parquet(full_path)
            df.columns = [c.lower() for c in df.columns]  # Lowercase columns for robustness

            # SLIDER: bars to use
            max_bars = len(df)
            lookback = st.sidebar.slider("Lookback Period", min_value=20, max_value=max_bars, value=min(500, max_bars), key="lookback_bars")

            # Only store DataFrame in session for use in analysis
            st.session_state['df_to_use'] = df.tail(lookback)

            # Market status
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📊 Market Status")

            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Price", f"{df['close'].iloc[-1]:.5f}")
            with col2:
                price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100 if len(df) > 1 else 0
                st.metric("Change", f"{price_change:+.2f}%")

        # Analysis options
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔬 Analysis Options")

        st.session_state['show_microstructure'] = st.sidebar.checkbox("🔍 Microstructure Analysis", True)
        st.session_state['show_smc'] = st.sidebar.checkbox("🧠 Smart Money Concepts", True)
        st.session_state['show_wyckoff'] = st.sidebar.checkbox("📈 Wyckoff Analysis", True)
        st.session_state['show_volume'] = st.sidebar.checkbox("📊 Volume Analysis", True)
        st.session_state['show_patterns'] = st.sidebar.checkbox("🎯 Pattern Recognition", True)

    def display_live_analysis(self):
        """Display live tick analysis with enhanced charts"""
        symbol = st.session_state.get('selected_pair', 'EURUSD')

        # Live status indicator
        st.markdown(
            f"<div style='text-align:center; color:#00ff00; font-size:1.2em; margin-bottom:1em;'>"
            f"🔴 LIVE - {symbol} - {datetime.now().strftime('%H:%M:%S')}"
            f"</div>",
            unsafe_allow_html=True
        )

        # Get live data
        latest_data = self.live_connector.get_live_data(symbol)

        if latest_data:
            # Display live metrics
            col1, col2, col3, col4, col5, col6 = st.columns(6)

            with col1:
                st.metric("Bid", f"{latest_data.get('bid', 0):.5f}")

            with col2:
                st.metric("Ask", f"{latest_data.get('ask', 0):.5f}")

            with col3:
                spread = latest_data.get('spread', 0)
                st.metric("Spread", spread)

            with col4:
                timestamp = latest_data.get('timestamp', 0)
                dt = datetime.fromtimestamp(timestamp)
                st.metric("Last Update", dt.strftime("%H:%M:%S"))

            with col5:
                # Add trend indicator if available
                if 'indicators' in latest_data:
                    rsi = latest_data['indicators'].get('rsi', 50)
                    rsi_color = "🟢" if rsi < 30 else "🔴" if rsi > 70 else "🟡"
                    st.metric("RSI", f"{rsi_color} {rsi:.1f}")
                else:
                    st.metric("RSI", "N/A")

            with col6:
                # Add volatility indicator
                if 'indicators' in latest_data:
                    atr = latest_data['indicators'].get('atr', 0)
                    st.metric("ATR", f"{atr:.5f}")
                else:
                    st.metric("ATR", "N/A")

            # Account info if available
            if 'account' in latest_data:
                st.subheader("💰 Account Information")
                acc_col1, acc_col2, acc_col3, acc_col4 = st.columns(4)

                account = latest_data['account']
                with acc_col1:
                    st.metric("Balance", f"${account.get('balance', 0):,.2f}")
                with acc_col2:
                    st.metric("Equity", f"${account.get('equity', 0):,.2f}")
                with acc_col3:
                    st.metric("Margin", f"${account.get('margin', 0):,.2f}")
                with acc_col4:
                    st.metric("Free Margin", f"${account.get('free_margin', 0):,.2f}")

            # Enhanced live tick chart
            st.subheader("📊 Live Tick Analysis")
            self.tick_chart.create_tick_chart(symbol=symbol, height=500)
            
            # Additional analysis sections
            if st.session_state.get('show_microstructure', True):
                self.display_live_microstructure_analysis(symbol, latest_data)
            
            if st.session_state.get('show_smc', True):
                self.display_live_smc_analysis(symbol, latest_data)
            
            # Auto-refresh logic
            if st.session_state.get('auto_refresh', True):
                time.sleep(st.session_state.get('refresh_interval', 2))
                st.rerun()
        
        else:
            st.warning(f"⏳ Waiting for live data from MT5 for {symbol}...")
            st.info("Make sure the EA is running on MT5 and sending data to Redis.")

    def create_enhanced_live_chart(self, symbol):
        """Create enhanced live tick chart similar to dashboard_mt5.py but with more features"""
        # Get historical data
        history = self.live_connector.get_tick_history(symbol, 100)
        
        if not history:
            st.warning("No historical tick data available")
            return
        
        # Create DataFrame
        df_data = []
        for h in history:
            df_data.append({
                'time': datetime.fromtimestamp(h.get('timestamp', 0)),
                'bid': h.get('bid', 0),
                'ask': h.get('ask', 0),
                'spread': h.get('spread', 0),
                'volume': h.get('volume', 0)
            })

        df = pd.DataFrame(df_data)

        if df.empty:
            st.warning("No tick data to display")
            return

        # Create enhanced subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.5, 0.2, 0.15, 0.15],
            subplot_titles=[
                f'{symbol} - Live Bid/Ask with Microstructure',
                'Spread Analysis',
                'Volume Profile',
                'Price Momentum'
            ]
        )

        # Main price chart with bid/ask
        fig.add_trace(
            go.Scatter(
                x=df['time'], 
                y=df['bid'],
                name='Bid',
                line=dict(color='limegreen', width=2.5),
                opacity=0.9
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['time'], 
                y=df['ask'],
                name='Ask',
                line=dict(color='crimson', width=2.5),
                opacity=0.9
            ),
            row=1, col=1
        )

        # Add current live price markers
        latest_data = self.live_connector.get_live_data(symbol)
        if latest_data:
            current_time = datetime.now()
            current_bid = latest_data.get('bid', df['bid'].iloc[-1])
            current_ask = latest_data.get('ask', df['ask'].iloc[-1])
            
            # Live price markers
            fig.add_trace(
                go.Scatter(
                    x=[current_time],
                    y=[current_bid],
                    mode='markers',
                    name='Live Bid',
                    marker=dict(size=15, color='lime', symbol='triangle-up'),
                    showlegend=False
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=[current_time],
                    y=[current_ask],
                    mode='markers',
                    name='Live Ask',
                    marker=dict(size=15, color='red', symbol='triangle-down'),
                    showlegend=False
                ),
                row=1, col=1
            )

        # Spread analysis with manipulation detection
        spread_mean = df['spread'].mean()
        spread_std = df['spread'].std()
        spread_threshold = spread_mean + 2 * spread_std
        
        # Color spreads based on threshold
        spread_colors = ['red' if s > spread_threshold else 'orange' for s in df['spread']]
        
        fig.add_trace(
            go.Scatter(
                x=df['time'], 
                y=df['spread'],
                name='Spread',
                line=dict(color='orange', width=2),
                mode='lines+markers',
                marker=dict(color=spread_colors, size=4)
            ),
            row=2, col=1
        )

        # Add spread threshold line
        fig.add_hline(
            y=spread_threshold, 
            line_dash="dash", 
            line_color="red", 
            opacity=0.7,
            annotation_text="Manipulation Threshold",
            row=2, col=1
        )

        # Volume analysis
        if 'volume' in df.columns and df['volume'].sum() > 0:
            colors = ['green' if i % 2 == 0 else 'red' for i in range(len(df))]
            fig.add_trace(
                go.Bar(
                    x=df['time'], 
                    y=df['volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=3, col=1
            )

        # Price momentum (simple price change)
        df['price_change'] = df['bid'].pct_change() * 10000  # in pips
        momentum_colors = ['green' if pc > 0 else 'red' for pc in df['price_change']]
        
        fig.add_trace(
            go.Bar(
                x=df['time'], 
                y=df['price_change'],
                name='Momentum (pips)',
                marker_color=momentum_colors,
                opacity=0.8
            ),
            row=4, col=1
        )

        # Enhanced styling
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
                bgcolor="rgba(0,0,0,0.8)"
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
                row=i, col=1
            )
            fig.update_yaxes(
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=False,
                showline=True,
                linecolor="gray",
                row=i, col=1
            )

        fig.update_xaxes(title_text="Time", row=4, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Spread", row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=3, col=1)
        fig.update_yaxes(title_text="Momentum", row=4, col=1)

        st.plotly_chart(fig, use_container_width=True)

    def display_live_microstructure_analysis(self, symbol, latest_data):
        """Display live microstructure analysis"""
        st.markdown("### 🔍 Live Microstructure Analysis")
        
        # Get tick history for analysis
        history = self.live_connector.get_tick_history(symbol, 50)
        
        if not history:
            st.warning("Not enough data for microstructure analysis")
            return
        
        # Calculate microstructure metrics
        spreads = [h.get('spread', 0) for h in history]
        volumes = [h.get('volume', 0) for h in history]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_spread = np.mean(spreads) if spreads else 0
            st.metric("Avg Spread (50 ticks)", f"{avg_spread:.1f}")
        
        with col2:
            spread_volatility = np.std(spreads) if spreads else 0
            st.metric("Spread Volatility", f"{spread_volatility:.2f}")
        
        with col3:
            max_spread = max(spreads) if spreads else 0
            current_spread = latest_data.get('spread', 0)
            spread_ratio = current_spread / max_spread if max_spread > 0 else 0
            st.metric("Spread Ratio", f"{spread_ratio:.2f}")
        
        with col4:
            # Manipulation score based on spread spikes
            spread_threshold = np.mean(spreads) + 2 * np.std(spreads) if spreads else 0
            manipulation_events = sum(1 for s in spreads if s > spread_threshold)
            manipulation_score = (manipulation_events / len(spreads)) * 100 if spreads else 0
            
            score_color = "🔴" if manipulation_score > 20 else "🟡" if manipulation_score > 10 else "🟢"
            st.metric("Manipulation Score", f"{score_color} {manipulation_score:.1f}%")

    def display_live_smc_analysis(self, symbol, latest_data):
        """Display live SMC analysis"""
        st.markdown("### 🧠 Live Smart Money Concepts")
        
        # This would integrate with your actual SMC analysis
        # For now, showing placeholder analysis
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Market Structure**")
            # You could add actual structure analysis here
            st.info("Bullish Structure Detected")
        
        with col2:
            st.markdown("**Order Flow**")
            # Add order flow analysis
            st.info("Smart Money Accumulation")
        
        with col3:
            st.markdown("**Liquidity Analysis**")
            # Add liquidity analysis
            st.info("High Liquidity Zone")

    def display_market_overview(self):
        """Display comprehensive market overview"""
        st.markdown("## 🌍 Market Overview & Analysis Summary")
        st.info("Switch to Live Mode for real-time tick analysis, or select a symbol for static analysis.")

    def display_ultimate_analysis(self):
        """Display comprehensive analysis dashboard (static mode)"""
        pair = st.session_state['selected_pair']
        timeframe = st.session_state['selected_timeframe']
        df = st.session_state['df_to_use']
        
        st.markdown(f"# 🚀 {pair} {timeframe} - Ultimate Analysis")
        st.info("This is static analysis mode. Switch to Live Mode for real-time tick data.")
        
        # Your existing static analysis code here
        # (abbreviated for space)

def main():
    """Main application entry point"""
    dashboard = UltimateZANFLOWDashboard()
    dashboard.create_main_dashboard()

if __name__ == "__main__":
    main()