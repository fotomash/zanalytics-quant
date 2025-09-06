#!/usr/bin/env python3
"""
ZANFLOW Multi-Asset Tick Manipulation Dashboard
Real-time visualization of tick data and manipulation detection
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import redis
import json
import time
from datetime import datetime, timedelta
import requests

# Page config
st.set_page_config(
    page_title="ZANFLOW Multi-Asset Tick Monitor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin: 10px 0;
    }
    .alert-high {
        background-color: #4a1a1a;
        border: 2px solid #ff4444;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .alert-medium {
        background-color: #4a3a1a;
        border: 2px solid #ff8844;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Redis connection
@st.cache_resource
def init_redis():
    return redis.Redis(host='localhost', port=6379, decode_responses=True)

r = init_redis()

# API endpoints
API_URL = "http://localhost:5000"

class TickManipulationDashboard:
    def __init__(self):
        self.symbols = []
        self.selected_symbols = []
        self.refresh_rate = 1

    def get_available_symbols(self):
        """Get all available symbols from the system"""
        try:
            # Get from API
            resp = requests.get(f"{API_URL}/summary", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                return list(data.get('symbols', {}).keys())
        except:
            pass

        # Fallback to Redis
        keys = r.keys("mt5:*:latest")
        symbols = []
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 2:
                symbols.append(parts[1])
        return sorted(set(symbols))

    def get_symbol_data(self, symbol):
        """Get latest data for a symbol"""
        try:
            # Get from Redis
            latest = r.get(f"mt5:{symbol}:latest")
            if latest:
                return json.loads(latest)
        except:
            pass
        return None

    def get_tick_history(self, symbol, count=100):
        """Get tick history for a symbol"""
        try:
            ticks = r.lrange(f"mt5:{symbol}:ticks", 0, count-1)
            return [json.loads(tick) for tick in ticks]
        except:
            return []

    def get_analysis_data(self, symbol):
        """Get analysis results for a symbol"""
        try:
            resp = requests.get(f"{API_URL}/analysis/{symbol}", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def create_manipulation_gauge(self, score, title="Manipulation Score"):
        """Create a gauge chart for manipulation score"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': 50},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 30], 'color': "lightgreen"},
                    {'range': [30, 50], 'color': "yellow"},
                    {'range': [50, 70], 'color': "orange"},
                    {'range': [70, 100], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        return fig

    def create_tick_chart(self, symbol, ticks):
        """Create tick chart with manipulation markers"""
        if not ticks:
            return None

        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['timestamp'], unit='s')

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f'{symbol} Price', 'Spread', 'Volume'),
            row_heights=[0.5, 0.25, 0.25]
        )

        # Price chart
        fig.add_trace(
            go.Scatter(x=df['time'], y=df['bid'], name='Bid', line=dict(color='green', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['time'], y=df['ask'], name='Ask', line=dict(color='red', width=1)),
            row=1, col=1
        )

        # Spread
        fig.add_trace(
            go.Scatter(x=df['time'], y=df['spread'], name='Spread', line=dict(color='orange')),
            row=2, col=1
        )

        # Volume
        fig.add_trace(
            go.Bar(x=df['time'], y=df['volume'], name='Volume', marker_color='lightblue'),
            row=3, col=1
        )

        fig.update_layout(height=600, showlegend=True, hovermode='x unified')
        fig.update_xaxes(title_text="Time", row=3, col=1)

        return fig

    def create_multi_symbol_heatmap(self, symbols):
        """Create heatmap of manipulation scores across symbols"""
        scores = []
        symbol_names = []

        for symbol in symbols[:20]:  # Limit to 20 symbols
            data = self.get_symbol_data(symbol)
            if data and 'tick_analysis' in data:
                score = data['tick_analysis'].get('manipulation_score', 0)
                scores.append(score)
                symbol_names.append(symbol)

        if not scores:
            return None

        # Create heatmap data
        z = np.array(scores).reshape(-1, 1)

        fig = go.Figure(data=go.Heatmap(
            z=z,
            y=symbol_names,
            x=['Manipulation Score'],
            colorscale='RdYlGn_r',
            text=z,
            texttemplate='%{text:.1f}',
            textfont={"size": 12},
            colorbar=dict(title="Score")
        ))

        fig.update_layout(
            title="Manipulation Scores Across Symbols",
            height=max(400, len(symbol_names) * 30),
            xaxis_title="",
            yaxis_title=""
        )

        return fig

    def display_alerts(self, symbol):
        """Display recent manipulation alerts"""
        try:
            alerts = r.lrange(f"alerts:{symbol}:manipulation", 0, 5)
            if alerts:
                st.subheader("🚨 Recent Alerts")
                for alert_json in alerts:
                    alert = json.loads(alert_json)
                    score = alert.get('score', 0)

                    alert_class = "alert-high" if score > 70 else "alert-medium"
                    st.markdown(
                        f'<div class="{alert_class}">'
                        f'<b>Score: {score:.1f}</b> - {alert["timestamp"]}<br>'
                        f'Spread Spikes: {alert["details"].get("spread_spikes", 0)} | '
                        f'Price Reversals: {alert["details"].get("price_reversals", 0)}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        except:
            pass

    def run(self):
        st.title("🎯 ZANFLOW Multi-Asset Tick Manipulation Monitor")

        # Sidebar
        st.sidebar.header("Configuration")

        # Get available symbols
        available_symbols = self.get_available_symbols()

        if not available_symbols:
            st.warning("No symbols found. Make sure the MT5 EA and API server are running.")
            return

        # Symbol selection
        view_mode = st.sidebar.radio("View Mode", ["Single Symbol", "Multi-Symbol Overview"])

        if view_mode == "Single Symbol":
            selected_symbol = st.sidebar.selectbox("Select Symbol", available_symbols)
            self.display_single_symbol(selected_symbol)
        else:
            self.display_multi_symbol_overview(available_symbols)

        # Refresh rate
        self.refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 1, 10, 1)

        # Auto refresh
        if st.sidebar.checkbox("Auto Refresh", True):
            time.sleep(self.refresh_rate)
            st.rerun()

    def display_single_symbol(self, symbol):
        """Display detailed view for single symbol"""
        col1, col2, col3, col4 = st.columns(4)

        # Get latest data
        data = self.get_symbol_data(symbol)
        analysis = self.get_analysis_data(symbol)

        if not data:
            st.error(f"No data available for {symbol}")
            return

        # Display metrics
        with col1:
            st.metric("Bid", f"{data.get('bid', 0):.5f}")
            st.metric("Ask", f"{data.get('ask', 0):.5f}")

        with col2:
            spread = data.get('spread', 0)
            st.metric("Spread", f"{spread:.1f} pips")
            st.metric("Volume", f"{data.get('volume', 0):,}")

        with col3:
            tick_analysis = data.get('tick_analysis', {})
            st.metric("Spread Spikes", tick_analysis.get('spread_spikes', 0))
            st.metric("Price Reversals", tick_analysis.get('price_reversals', 0))

        with col4:
            if analysis:
                st.metric("Total Ticks", f"{analysis.get('tick_count', 0):,}")
                enriched = analysis.get('enriched_bars', {})
                if enriched:
                    st.metric("250-Bar Change", f"{enriched.get('change_percent', 0):.2f}%")

        # Manipulation gauge
        st.subheader("Manipulation Detection")
        col1, col2 = st.columns(2)

        with col1:
            score = data.get('tick_analysis', {}).get('manipulation_score', 0)
            fig = self.create_manipulation_gauge(score)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            self.display_alerts(symbol)

        # Tick chart
        st.subheader("Tick Analysis")
        ticks = self.get_tick_history(symbol, 500)
        if ticks:
            fig = self.create_tick_chart(symbol, ticks)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        # Analysis results
        if analysis and 'microstructure_analysis' in analysis and analysis['microstructure_analysis']:
            st.subheader("Microstructure Analysis Results")

            results = analysis['microstructure_analysis'].get('results', {})
            if results:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**Manipulation Patterns**")
                    st.write(f"- Spread Spikes: {results.get('spread_spikes', 0)}")
                    st.write(f"- Stop Hunts: {results.get('stop_hunts', 0)}")
                    st.write(f"- Liquidity Sweeps: {results.get('liquidity_sweeps', 0)}")

                with col2:
                    st.write("**Wyckoff Analysis**")
                    wyckoff = results.get('wyckoff_phases', {})
                    for phase, count in wyckoff.items():
                        st.write(f"- Phase {phase}: {count}")

                with col3:
                    st.write("**SMC Analysis**")
                    st.write(f"- Bullish FVGs: {results.get('bullish_fvgs', 0)}")
                    st.write(f"- Bearish FVGs: {results.get('bearish_fvgs', 0)}")
                    st.write(f"- High Inducements: {results.get('high_inducements', 0)}")
                    st.write(f"- Low Inducements: {results.get('low_inducements', 0)}")

        # Trigger analysis button
        if st.button(f"🔍 Run Deep Analysis for {symbol}"):
            with st.spinner("Running deep analysis..."):
                try:
                    resp = requests.post(f"{API_URL}/trigger_analysis/{symbol}")
                    if resp.status_code == 200:
                        st.success("Analysis triggered successfully!")
                    else:
                        st.error("Failed to trigger analysis")
                except Exception as e:
                    st.error(f"Error: {e}")

    def display_multi_symbol_overview(self, symbols):
        """Display overview of multiple symbols"""
        st.subheader("Multi-Symbol Manipulation Overview")

        # Create heatmap
        fig = self.create_multi_symbol_heatmap(symbols)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        # High manipulation alerts
        st.subheader("🚨 High Manipulation Symbols")

        high_manipulation = []
        for symbol in symbols:
            data = self.get_symbol_data(symbol)
            if data and 'tick_analysis' in data:
                score = data['tick_analysis'].get('manipulation_score', 0)
                if score > 50:
                    high_manipulation.append({
                        'Symbol': symbol,
                        'Score': score,
                        'Bid': data.get('bid', 0),
                        'Ask': data.get('ask', 0),
                        'Spread': data.get('spread', 0),
                        'Spread Spikes': data['tick_analysis'].get('spread_spikes', 0),
                        'Price Reversals': data['tick_analysis'].get('price_reversals', 0)
                    })

        if high_manipulation:
            df = pd.DataFrame(high_manipulation)
            df = df.sort_values('Score', ascending=False)
            st.dataframe(
                df.style.background_gradient(subset=['Score'], cmap='RdYlGn_r'),
                use_container_width=True
            )
        else:
            st.info("No high manipulation detected across monitored symbols")

        # Symbol grid
        st.subheader("All Symbols Status")

        cols = st.columns(4)
        for i, symbol in enumerate(symbols[:20]):  # Limit display
            col_idx = i % 4
            with cols[col_idx]:
                data = self.get_symbol_data(symbol)
                if data:
                    score = data.get('tick_analysis', {}).get('manipulation_score', 0)
                    color = "🔴" if score > 50 else "🟡" if score > 30 else "🟢"

                    st.markdown(
                        f'<div class="metric-card">'
                        f'<h4>{symbol}</h4>'
                        f'<p>Price: {data.get("bid", 0):.5f}</p>'
                        f'<p>Spread: {data.get("spread", 0):.1f}</p>'
                        f'<p>Manipulation: {color} {score:.1f}</p>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # API summary
        try:
            resp = requests.get(f"{API_URL}/summary")
            if resp.status_code == 200:
                summary = resp.json()
                st.subheader("System Overview")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Symbols", summary.get('symbols_tracked', 0))

                with col2:
                    total_ticks = sum(s.get('tick_count', 0) for s in summary.get('symbols', {}).values())
                    st.metric("Total Ticks Processed", f"{total_ticks:,}")

                with col3:
                    analyzed = sum(1 for s in summary.get('symbols', {}).values() if s.get('has_analysis'))
                    st.metric("Symbols Analyzed", analyzed)
        except:
            pass

# Main execution
if __name__ == "__main__":
    dashboard = TickManipulationDashboard()
    dashboard.run()
