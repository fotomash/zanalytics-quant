#!/usr/bin/env python3
"""
ZANFLOW Wyckoff Analysis Dashboard v6.0 - Interactive & API Driven
Connects to the Zanalytics API to fetch and dynamically visualize
Wyckoff, VSA, SMC, and Microstructure analysis on the main chart.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests

# --- Configuration ---
# In a real application, this would come from a central config file or environment variable
API_BASE_URL = "http://localhost:5010"

st.set_page_config(
    page_title="Wyckoff VSA Analysis - ZANFLOW v12",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- API Client Functions ---

def get_api_status():
    """Checks the status of the Zanalytics API."""
    try:
        response = requests.get(f"{API_BASE_URL}/status", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}


def get_analysis_summary(symbol: str):
    """Fetches the complete analysis summary for a symbol from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/analysis/summary/{symbol}", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch analysis for {symbol}: {e}")
        return None


def get_ohlc_data(symbol: str, timeframe: str):
    """Fetches OHLC data from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/data/ohlc/{symbol}/{timeframe}", timeout=30)
        response.raise_for_status()
        ohlc_data = response.json().get('ohlc_data', [])
        if ohlc_data:
            df = pd.DataFrame.from_records(ohlc_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch OHLC data for {symbol}/{timeframe}: {e}")
        return pd.DataFrame()


# --- UI Rendering Functions ---

def render_main_chart(df: pd.DataFrame, analysis_summary: dict, symbol: str, timeframe: str):
    """
    Generates the main Plotly chart and dynamically overlays analysis from the API.
    This function is now the interactive heart of the dashboard.
    """
    if df.empty:
        st.warning("No data available to plot.")
        return

    fig = go.Figure()

    # Add Candlestick trace
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC'
    ))

    # --- INTELLIGENCE LAYER: Dynamic Annotations from API ---

    # 1. Plot Wyckoff Phases
    wyckoff_phases = analysis_summary.get('wyckoff_phases', {}).get(timeframe, {})
    for phase_name, phase_data in wyckoff_phases.items():
        if isinstance(phase_data, dict) and "start_time" in phase_data and "end_time" in phase_data:
            fig.add_vrect(
                x0=phase_data["start_time"], x1=phase_data["end_time"],
                fillcolor="rgba(76, 175, 80, 0.15)", layer="below", line_width=0,
                annotation_text=phase_name, annotation_position="top left"
            )

    # 2. Plot SMC Points of Interest (FVGs, Order Blocks)
    smc_analysis = analysis_summary.get('structure_analysis', {}).get(timeframe, {})
    pois = smc_analysis.get('points_of_interest', [])
    for poi in pois:
        if "start_time" in poi and "end_time" in poi and "high" in poi and "low" in poi:
            fig.add_shape(
                type="rect",
                x0=poi["start_time"], y0=poi["low"],
                x1=poi["end_time"], y1=poi["high"],
                line=dict(color="rgba(255, 165, 0, 0.5)", width=1, dash="dot"),
                fillcolor="rgba(255, 165, 0, 0.2)",
                layer="below"
            )
            fig.add_annotation(x=poi["start_time"], y=poi["high"], text=poi.get("type", "POI"), showarrow=False,
                               yshift=10)

    # 3. Plot Liquidity Sweeps
    liquidity_events = analysis_summary.get('microstructure', {}).get('liquidity_events', [])
    for event in liquidity_events:
        if "timestamp" in event and "price" in event:
            fig.add_trace(go.Scatter(
                x=[event["timestamp"]],
                y=[event["price"]],
                mode='markers',
                marker=dict(symbol='x', color='red', size=10),
                name=f"Liquidity Sweep ({event.get('type')})"
            ))

    fig.update_layout(
        title=f"Interactive Wyckoff & SMC Analysis: {symbol} ({timeframe})",
        xaxis_title=None,
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_key_metrics(analysis_summary: dict):
    """Displays key performance indicators and analysis scores."""
    st.subheader("📈 Key Metrics & System State")

    if not analysis_summary:
        st.warning("Analysis summary not available.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Symbol", analysis_summary.get('symbol', 'N/A'))

    with col2:
        phases = analysis_summary.get('wyckoff_phases', {})
        dominant_phase = "N/A"
        if phases:
            # Find the analysis for the most relevant timeframe (e.g., first one available)
            first_tf_analysis = next(iter(phases.values()), {})
            dominant_phase = first_tf_analysis.get('dominant_phase', 'N/A')
        st.metric("Dominant Wyckoff Phase", dominant_phase)

    with col3:
        manipulation_score = analysis_summary.get('microstructure', {}).get('manipulation_score', 0.0)
        st.metric("Manipulation Score", f"{manipulation_score:.2f}")

    with col4:
        consensus = analysis_summary.get('agent_consensus', {})
        bias = consensus.get('bias', 'Neutral')
        st.metric("Agent Consensus Bias", bias)


# --- Main Application ---

def main():
    """The main Streamlit application function."""
    st.markdown("<h1>📊 ZANFLOW Wyckoff Analysis v6.0</h1>", unsafe_allow_html=True)
    st.markdown("### API-Driven Interactive Institutional Analysis")

    # --- Sidebar for Controls ---
    with st.sidebar:
        st.header("🎛️ Controls")

        api_status = get_api_status()
        if api_status.get('status') == 'operational':
            st.success(f"API Status: {api_status['status'].upper()}")
            active_symbols = api_status.get('data_feeds', {}).get('active_symbols', ['EURUSD', 'XAUUSD'])
            selected_symbol = st.selectbox("Select Symbol", options=active_symbols)
        else:
            st.error(f"API Connection Failed: {api_status.get('message', 'Unknown error')}")
            st.stop()

        selected_tf = st.selectbox("Select Timeframe", options=["H1", "M15", "M5"])

    # --- Main Content ---
    if selected_symbol and selected_tf:
        with st.spinner(f"Fetching latest intelligence for {selected_symbol}..."):
            analysis_summary = get_analysis_summary(selected_symbol)
            ohlc_df = get_ohlc_data(selected_symbol, selected_tf)

        if analysis_summary and not ohlc_df.empty:
            render_key_metrics(analysis_summary)
            render_main_chart(ohlc_df, analysis_summary, selected_symbol, selected_tf)

            with st.expander("🔬 View Full Analysis JSON from API"):
                st.json(analysis_summary)
        else:
            st.error(f"Could not retrieve complete data for {selected_symbol}. Please check the backend services.")


if __name__ == "__main__":
    main()
