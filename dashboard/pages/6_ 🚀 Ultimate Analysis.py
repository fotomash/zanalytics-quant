#!/usr/bin/env python3
"""
Enhanced ZANFLOW Ultimate Analysis with Live Tick Integration
Combines sophisticated analysis with real-time tick data and enrichment
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import redis
import json
import requests
import time
from datetime import datetime, timedelta
import base64
from pathlib import Path
import re
import warnings

warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="ZANFLOW Ultimate Live Analysis",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)


class LiveTickConnector:
    """Enhanced live data connector with tick analysis integration"""

    def __init__(self, api_url="http://mm20.local:8080"):
        self.api_url = api_url
        self.redis_client = self._init_redis()
        self._test_connection()

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            return r
        except:
            return None

    def _test_connection(self):
        """Test API connection"""
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                st.sidebar.success("✅ Connected to mm20.local")
                return True
            else:
                st.sidebar.warning("⚠️ API connected but returned error")
                return False
        except Exception:
            st.sidebar.error("❌ Cannot connect to mm20.local:8080")
            return False

    def get_symbols(self):
        """Get available symbols"""
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def get_live_data(self, symbol):
        """Get live enriched data for symbol"""
        try:
            response = requests.get(f"{self.api_url}/data/{symbol}", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def get_tick_history(self, symbol, limit=500):
        """Get tick history from Redis"""
        if not self.redis_client:
            return []

        try:
            key = f"mt5:{symbol}:ticks"
            ticks = self.redis_client.lrange(key, 0, limit - 1)
            return [json.loads(tick) for tick in ticks]
        except:
            return []

    def get_enriched_analysis(self, symbol):
        """Get enriched microstructure analysis"""
        if not self.redis_client:
            return None

        try:
            key = f"analysis:{symbol}:microstructure"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except:
            pass
        return None


def scan_parquet_files(data_dir):
    """Scan directory for Parquet files"""
    files = []
    for f in Path(data_dir).rglob("*.parquet"):
        name = f.stem.upper()
        parent = f.parent.name.upper()

        if re.match(r"\d+[A-Z]+", name):
            symbol = parent
            timeframe = name
        elif re.match(r"\d+[A-Z]+", parent):
            symbol = name
            timeframe = parent
        else:
            m = re.match(r"(.*?)_(\d+[a-zA-Z]+)$", name, re.IGNORECASE)
            if m:
                symbol, timeframe = m.group(1).upper(), m.group(2).upper()
            else:
                continue

        files.append((symbol, timeframe, f.relative_to(data_dir)))
    return files


class EnhancedUltimateAnalysis:
    """Enhanced Ultimate Analysis with Live Tick Integration"""

    def __init__(self, data_directory=None):
        if data_directory is None:
            data_directory = st.secrets.get("PARQUET_DATA_DIR", "./data")
        self.data_dir = Path(data_directory)
        self.live_connector = LiveTickConnector()

        # Initialize session state for live mode
        if 'live_mode' not in st.session_state:
            st.session_state.live_mode = False
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 2

    def apply_styling(self):
        """Apply ZANFLOW styling"""

        def get_image_as_base64(path):
            try:
                with open(path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode()
            except Exception:
                return None

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

            section[data-testid="stSidebar"] {{
                background-color: rgba(0,0,0,0.8) !important;
                box-shadow: none !important;
            }}

            .main .block-container {{
                background-color: rgba(0,0,0,0.025) !important;
            }}

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
        """Create ZANFLOW header"""
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

    def create_sidebar_controls(self):
        """Enhanced sidebar with live controls"""
        st.sidebar.title("🎛️ Live Analysis Control")

        # Live mode toggle
        st.sidebar.markdown("### 🔴 Live Mode")
        col1, col2 = st.sidebar.columns(2)

        if col1.button("▶️ Go Live"):
            st.session_state.live_mode = True
            st.rerun()

        if col2.button("⏹️ Stop Live"):
            st.session_state.live_mode = False
            st.rerun()

        # Live mode settings
        if st.session_state.live_mode:
            st.sidebar.success("🔴 LIVE MODE ACTIVE")
            st.session_state.auto_refresh = st.sidebar.checkbox("Auto Refresh", True)
            st.session_state.refresh_interval = st.sidebar.slider(
                "Refresh Rate (seconds)", 1, 10, 2
            )

            # Available live symbols
            live_symbols = self.live_connector.get_symbols()
            if live_symbols:
                selected_live_symbol = st.sidebar.selectbox(
                    "📡 Live Symbol", live_symbols, key="live_symbol"
                )
                st.session_state.selected_pair = selected_live_symbol

                # Manual refresh
                if st.sidebar.button("🔄 Refresh Now"):
                    st.rerun()
            else:
                st.sidebar.warning("No live symbols available")
        else:
            # Static analysis mode
            st.sidebar.info("📊 Static Analysis Mode")

            # Parquet file selection
            file_info = scan_parquet_files(self.data_dir)
            symbols = sorted({sym for sym, _, _ in file_info})

            if symbols:
                selected_pair = st.sidebar.selectbox("📈 Select Symbol", symbols, key="selected_pair")

                available_timeframes = sorted({tf for sym, tf, _ in file_info if sym == selected_pair})
                if available_timeframes:
                    selected_timeframe = st.sidebar.selectbox(
                        "⏱️ Select Timeframe", available_timeframes, key="selected_timeframe"
                    )

                    # Load static data
                    try:
                        rel_path = next(
                            f for sym, tf, f in file_info if sym == selected_pair and tf == selected_timeframe)
                        full_path = self.data_dir / rel_path
                        df = pd.read_parquet(full_path)
                        df.columns = [c.lower() for c in df.columns]

                        max_bars = len(df)
                        lookback = st.sidebar.slider(
                            "Lookback Period", min_value=20, max_value=max_bars,
                            value=min(500, max_bars), key="lookback_bars"
                        )

                        st.session_state['df_to_use'] = df.tail(lookback)

                    except Exception as e:
                        st.sidebar.error(f"Error loading data: {e}")

        # Analysis options
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔬 Analysis Options")

        st.session_state['show_microstructure'] = st.sidebar.checkbox("🔍 Microstructure Analysis", True)
        st.session_state['show_smc'] = st.sidebar.checkbox("🧠 Smart Money Concepts", True)
        st.session_state['show_wyckoff'] = st.sidebar.checkbox("📈 Wyckoff Analysis", True)
        st.session_state['show_volume'] = st.sidebar.checkbox("📊 Volume Analysis", True)
        st.session_state['show_patterns'] = st.sidebar.checkbox("🎯 Pattern Recognition", True)

    def create_live_tick_chart(self, symbol):
        """Create enhanced live tick chart with enriched data"""
        live_data = self.live_connector.get_live_data(symbol)
        tick_history = self.live_connector.get_tick_history(symbol, 500)
        enriched_analysis = self.live_connector.get_enriched_analysis(symbol)

        if not live_data and not tick_history:
            st.warning(f"No live data available for {symbol}")
            return

        # Create subplots for comprehensive analysis
        fig = make_subplots(
            rows=5, cols=1,
            subplot_titles=[
                f"{symbol} - Live Tick Analysis with Microstructure",
                "Spread Analysis & Manipulation Detection",
                "Volume Profile & Liquidity",
                "RSI & Momentum",
                "Wyckoff Phase Analysis"
            ],
            vertical_spacing=0.04,
            row_heights=[0.4, 0.2, 0.15, 0.15, 0.1],
            shared_xaxes=True
        )

        if tick_history:
            # Convert tick history to DataFrame
            df_ticks = pd.DataFrame(tick_history)
            df_ticks['datetime'] = pd.to_datetime(df_ticks['timestamp'], unit='s')
            df_ticks['mid_price'] = (df_ticks['bid'] + df_ticks['ask']) / 2
            df_ticks['spread_pips'] = (df_ticks['ask'] - df_ticks['bid']) * 10000

            # Main price chart with tick data
            fig.add_trace(go.Scatter(
                x=df_ticks['datetime'],
                y=df_ticks['bid'],
                mode='lines',
                name='Bid',
                line=dict(color='limegreen', width=1.5),
                opacity=0.8
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=df_ticks['datetime'],
                y=df_ticks['ask'],
                mode='lines',
                name='Ask',
                line=dict(color='crimson', width=1.5),
                opacity=0.8
            ), row=1, col=1)

            # Add current live price markers
            if live_data:
                current_time = datetime.now()
                current_bid = live_data.get('bid', df_ticks['bid'].iloc[-1])
                current_ask = live_data.get('ask', df_ticks['ask'].iloc[-1])

                # Live price markers
                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[current_bid],
                    mode='markers',
                    name='Live Bid',
                    marker=dict(size=12, color='lime', symbol='triangle-up'),
                    showlegend=False
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=[current_time],
                    y=[current_ask],
                    mode='markers',
                    name='Live Ask',
                    marker=dict(size=12, color='red', symbol='triangle-down'),
                    showlegend=False
                ), row=1, col=1)

            # Spread analysis with manipulation detection
            if enriched_analysis and 'spread_spikes' in enriched_analysis:
                # Highlight spread spikes
                spread_threshold = df_ticks['spread_pips'].mean() + 2 * df_ticks['spread_pips'].std()
                spike_mask = df_ticks['spread_pips'] > spread_threshold

                fig.add_trace(go.Scatter(
                    x=df_ticks['datetime'],
                    y=df_ticks['spread_pips'],
                    mode='lines',
                    name='Spread',
                    line=dict(color='orange', width=1.5)
                ), row=2, col=1)

                # Mark spread spikes
                if spike_mask.any():
                    spike_data = df_ticks[spike_mask]
                    fig.add_trace(go.Scatter(
                        x=spike_data['datetime'],
                        y=spike_data['spread_pips'],
                        mode='markers',
                        name='Spread Spikes',
                        marker=dict(size=8, color='yellow', symbol='star'),
                        showlegend=False
                    ), row=2, col=1)
            else:
                fig.add_trace(go.Scatter(
                    x=df_ticks['datetime'],
                    y=df_ticks['spread_pips'],
                    mode='lines',
                    name='Spread',
                    line=dict(color='orange', width=1.5)
                ), row=2, col=1)

            # Volume analysis
            if 'volume' in df_ticks.columns:
                colors = ['green' if i % 2 == 0 else 'red' for i in range(len(df_ticks))]
                fig.add_trace(go.Bar(
                    x=df_ticks['datetime'],
                    y=df_ticks['volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ), row=3, col=1)

            # RSI if available in enriched data
            if enriched_analysis and 'rsi' in enriched_analysis:
                rsi_values = [enriched_analysis['rsi']] * len(df_ticks)
                fig.add_trace(go.Scatter(
                    x=df_ticks['datetime'],
                    y=rsi_values,
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple', width=2)
                ), row=4, col=1)

                # RSI levels
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=4, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=4, col=1)

            # Wyckoff phase analysis
            if enriched_analysis and 'wyckoff_phase' in enriched_analysis:
                phase = enriched_analysis['wyckoff_phase']
                phase_colors = {
                    'accumulation': 'blue',
                    'markup': 'green',
                    'distribution': 'orange',
                    'markdown': 'red'
                }

                phase_y = [1 if phase == 'accumulation' else
                           2 if phase == 'markup' else
                           3 if phase == 'distribution' else
                           4 if phase == 'markdown' else 0] * len(df_ticks)

                fig.add_trace(go.Scatter(
                    x=df_ticks['datetime'],
                    y=phase_y,
                    mode='lines',
                    name=f'Wyckoff: {phase}',
                    line=dict(color=phase_colors.get(phase, 'gray'), width=3)
                ), row=5, col=1)

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
                bgcolor="rgba(0,0,0,0.8)"
            ),
            margin=dict(l=50, r=50, t=100, b=50),
            height=800,
            hovermode='x unified'
        )

        # Update axes
        for i in range(1, 6):
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

        st.plotly_chart(fig, use_container_width=True)

    def display_live_metrics(self, symbol):
        """Display live metrics with enriched data"""
        live_data = self.live_connector.get_live_data(symbol)
        enriched_analysis = self.live_connector.get_enriched_analysis(symbol)

        if not live_data:
            st.warning("No live data available")
            return

        # Main metrics row
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.metric("Bid", f"{live_data.get('bid', 0):.5f}")

        with col2:
            st.metric("Ask", f"{live_data.get('ask', 0):.5f}")

        with col3:
            spread = live_data.get('ask', 0) - live_data.get('bid', 0)
            st.metric("Spread", f"{spread:.5f}")

        with col4:
            if enriched_analysis and 'rsi' in enriched_analysis:
                rsi = enriched_analysis['rsi']
                rsi_color = "🟢" if rsi < 30 else "🔴" if rsi > 70 else "🟡"
                st.metric("RSI", f"{rsi_color} {rsi:.1f}")
            else:
                st.metric("RSI", "N/A")

        with col5:
            if enriched_analysis and 'manipulation_score' in enriched_analysis:
                score = enriched_analysis['manipulation_score']
                score_color = "🔴" if score > 70 else "🟡" if score > 40 else "🟢"
                st.metric("Manipulation", f"{score_color} {score:.1f}")
            else:
                st.metric("Manipulation", "N/A")

        with col6:
            timestamp = live_data.get('timestamp', time.time())
            dt = datetime.fromtimestamp(timestamp)
            st.metric("Last Update", dt.strftime("%H:%M:%S"))

        # Enriched analysis display
        if enriched_analysis:
            st.markdown("### 🔬 Live Microstructure Analysis")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("**Manipulation Events**")
                st.write(f"Spread Spikes: {enriched_analysis.get('spread_spikes', 0)}")
                st.write(f"Stop Hunts: {enriched_analysis.get('stop_hunts', 0)}")
                st.write(f"Liquidity Sweeps: {enriched_analysis.get('liquidity_sweeps', 0)}")

            with col2:
                st.markdown("**Wyckoff Analysis**")
                phase = enriched_analysis.get('wyckoff_phase', 'Unknown')
                st.write(f"Current Phase: {phase.title()}")
                st.write(f"Phase Strength: {enriched_analysis.get('phase_strength', 0):.2f}")

            with col3:
                st.markdown("**SMC Analysis**")
                st.write(f"Bullish FVGs: {enriched_analysis.get('bullish_fvgs', 0)}")
                st.write(f"Bearish FVGs: {enriched_analysis.get('bearish_fvgs', 0)}")
                st.write(f"Order Blocks: {enriched_analysis.get('order_blocks', 0)}")

            with col4:
                st.markdown("**Market Structure**")
                structure = enriched_analysis.get('market_structure', 'Unknown')
                st.write(f"Structure: {structure}")
                st.write(f"Trend Strength: {enriched_analysis.get('trend_strength', 0):.2f}")

    def run_main_dashboard(self):
        """Main dashboard execution"""
        self.apply_styling()
        self.create_header()
        self.create_sidebar_controls()

        # Main content based on mode
        if st.session_state.live_mode and st.session_state.get('selected_pair'):
            symbol = st.session_state.selected_pair

            # Live status indicator
            st.markdown(
                f"<div style='text-align:center; color:#00ff00; font-size:1.2em; margin-bottom:1em;'>"
                f"🔴 LIVE - {symbol} - {datetime.now().strftime('%H:%M:%S')}"
                f"</div>",
                unsafe_allow_html=True
            )

            # Live metrics
            self.display_live_metrics(symbol)

            # Live tick chart
            st.markdown("### 📊 Live Tick Analysis")
            self.create_live_tick_chart(symbol)

            # Additional analysis sections
            if st.session_state.get('show_microstructure', True):
                self.display_microstructure_insights(symbol)

            # Auto-refresh logic
            if st.session_state.auto_refresh:
                time.sleep(st.session_state.refresh_interval)
                st.rerun()

        elif 'df_to_use' in st.session_state:
            # Static analysis mode
            symbol = st.session_state.get('selected_pair', 'Unknown')
            timeframe = st.session_state.get('selected_timeframe', 'Unknown')

            st.markdown(f"# 📊 {symbol} {timeframe} - Static Analysis")
            st.info("Switch to Live Mode for real-time tick analysis")

            # Display static analysis here (your existing code)
            df = st.session_state['df_to_use']
            self.display_static_analysis(df, symbol, timeframe)

        else:
            # Welcome screen
            st.markdown("## 🌍 ZANFLOW Ultimate Analysis")
            st.info(
                "Select a symbol from the sidebar to begin analysis, or switch to Live Mode for real-time tick data.")

    def display_microstructure_insights(self, symbol):
        """Display microstructure analysis insights"""
        enriched_analysis = self.live_connector.get_enriched_analysis(symbol)

        if not enriched_analysis:
            return

        st.markdown("### 🔬 Advanced Microstructure Insights")

        # Manipulation timeline
        if 'manipulation_events' in enriched_analysis:
            events = enriched_analysis['manipulation_events']
            if events:
                st.markdown("#### 🚨 Recent Manipulation Events")
                for event in events[-5:]:  # Show last 5 events
                    event_time = datetime.fromtimestamp(event.get('timestamp', 0))
                    event_type = event.get('type', 'Unknown')
                    severity = event.get('severity', 'Low')

                    severity_color = "🔴" if severity == 'High' else "🟡" if severity == 'Medium' else "🟢"
                    st.markdown(f"**{event_time.strftime('%H:%M:%S')}** - {severity_color} {event_type}")

        # Liquidity analysis
        if 'liquidity_analysis' in enriched_analysis:
            liquidity = enriched_analysis['liquidity_analysis']

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 💧 Liquidity Zones")
                st.write(f"High Liquidity: {liquidity.get('high_zones', 0)}")
                st.write(f"Low Liquidity: {liquidity.get('low_zones', 0)}")

            with col2:
                st.markdown("#### 🎯 Support/Resistance")
                st.write(f"Support Level: {liquidity.get('support', 0):.5f}")
                st.write(f"Resistance Level: {liquidity.get('resistance', 0):.5f}")

    def display_static_analysis(self, df, symbol, timeframe):
        """Display static analysis (fallback)"""
        st.markdown("### 📊 Static Analysis")

        # Basic metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Current Price", f"{df['close'].iloc[-1]:.5f}")

        with col2:
            price_change = df['close'].iloc[-1] - df['close'].iloc[0]
            st.metric("Change", f"{price_change:+.5f}")

        with col3:
            if 'volume' in df.columns:
                st.metric("Volume", f"{df['volume'].iloc[-1]:,.0f}")

        with col4:
            volatility = df['close'].pct_change().std()
            st.metric("Volatility", f"{volatility:.5f}")

        # Basic price chart
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ))

        fig.update_layout(
            template="plotly_dark",
            title=f"{symbol} {timeframe} Price Chart",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main application entry point"""
    dashboard = EnhancedUltimateAnalysis()
    dashboard.run_main_dashboard()


if __name__ == "__main__":
    main()