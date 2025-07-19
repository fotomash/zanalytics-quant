#!/usr/bin/env python3
"""
Enhanced Wyckoff Analysis Dashboard v4.0 - with JSON Auto-Loading
Advanced Wyckoff Method Implementation with VSA and Market Structure Analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
from pathlib import Path
from datetime import datetime, timedelta, date
import warnings
from typing import Dict, List, Tuple, Optional
import logging
import json

from wyckoff_analyzer import WyckoffAnalyzer

st.set_page_config(
    page_title="Wyckoff VSA Analysis - QRT Pro v4.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

#
# Helper functions
#

# List all .parquet files in the data_dir (recursive)
def list_parquet_files(data_dir):
    """Return a list of all .parquet files in the data_dir (recursive)."""
    data_dir = Path(data_dir)
    return list(data_dir.rglob("*.parquet"))

# Load Parquet data helper
def load_parquet_data(data_dir, file_name):
    """Load a Parquet file from the given directory and return a pandas DataFrame."""
    data_path = Path(data_dir) / file_name
    return pd.read_parquet(data_path)


# Wyckoff chart creation helper
def create_wyckoff_chart(df, analysis, symbol):
    """
    Generate a basic Plotly Figure for Wyckoff analysis.
    This is a placeholder; replace with detailed plotting logic as needed.
    """
    # Determine time column
    time_col = 'datetime' if 'datetime' in df.columns else 'timestamp'
    # Ensure datetime type
    df[time_col] = pd.to_datetime(df[time_col])
    # Build line chart of closing price
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df['close'],
            mode='lines',
            name='Close Price'
        )
    )
    # Layout settings
    fig.update_layout(
        title=f"Wyckoff Analysis Chart: {symbol}",
        xaxis_title="Time",
        yaxis_title="Price",
        showlegend=True
    )
    return fig


# ====
# JSON LOADING FUNCTIONS
# ====
def load_comprehensive_json(symbol, json_dir=None):
    """Load comprehensive JSON analysis for a symbol"""
    if json_dir is None:
        json_dir = st.secrets.get("JSONdir", "./midas_analysis")

    # Try multiple possible JSON file patterns
    possible_patterns = [
        f"{symbol}_comprehensive.json",
        f"{symbol}_analysis.json",
        f"{symbol}.json",
        f"{symbol}_tick.json"
    ]

    for pattern in possible_patterns:
        json_path = Path(f"{json_dir}/{pattern}")
        if json_path.exists():
            try:
                with open(json_path, "r") as f:
                    content = f.read()
                    if content.strip():
                        data = json.loads(content)
                        return data, pattern
                    else:
                        continue
            except Exception as e:
                st.warning(f"Could not parse JSON file {pattern}: {e}")
                continue

    return None, None

def load_zanflow_json(symbol, json_dir=None):
    """Load ZANFLOW microstructure analysis JSON"""
    if json_dir is None:
        json_dir = st.secrets.get("JSONdir", "./midas_analysis")

    zanflow_path = Path(f"{json_dir}/{symbol}/{symbol}_*tick.json")
    import glob

    files = glob.glob(str(zanflow_path))
    if files:
        try:
            with open(files[0], "r") as f:
                return json.loads(f.read()), files[0]
        except Exception as e:
            st.warning(f"Could not load ZANFLOW data: {e}")

    return None, None

def merge_json_insights(comprehensive_json, zanflow_json):
    """Merge insights from different JSON sources"""
    merged = {}

    if comprehensive_json:
        merged.update(comprehensive_json)

    if zanflow_json:
        # Add ZANFLOW specific insights
        merged['zanflow_analysis'] = {
            'manipulation_score': zanflow_json.get('manipulation', {}).get('spread_spikes', {}).get('count', 0),
            'wyckoff_phases': zanflow_json.get('wyckoff', {}).get('phases', {}),
            'smc_analysis': zanflow_json.get('smc', {}),
            'inducement_data': zanflow_json.get('inducement', {})
        }

        # Extract strategy insights
        if 'inducement' in zanflow_json and 'strategy_insights' in zanflow_json['inducement']:
            merged['strategy_insights'] = zanflow_json['inducement']['strategy_insights']

    return merged

# ====
# ENHANCED TRADE SETUP RENDERING
# ====
def render_enhanced_trade_setups(symbol, json_data):
    """Enhanced trade setup rendering with JSON data integration"""
    if not json_data:
        st.info("No JSON analysis data available for trade setups")
        return

    # Check for strategy insights from ZANFLOW
    if 'strategy_insights' in json_data:
        strategy_data = json_data['strategy_insights']

        st.subheader("🎯 Strategy Insights")

        # V5 Strategy (Basic SMC)
        if 'v5_strategy' in strategy_data:
            v5 = strategy_data['v5_strategy']
            st.markdown(f"""
            **V5 Strategy (Smart Money Concepts)**
            - Total FVGs: {v5.get('total_fvgs', 'N/A')}
            - Market Bias: {v5.get('bias', 'N/A')}
            """)

        # V10 Strategy (Wyckoff)
        if 'v10_strategy' in strategy_data:
            v10 = strategy_data['v10_strategy']
            st.markdown(f"""
            **V10 Strategy (Advanced Wyckoff)**
            - Dominant Phase: {v10.get('dominant_phase', 'N/A')}
            - Phase Distribution: {v10.get('phase_distribution', 'N/A')}
            """)

        # V12 Strategy (Full ZANFLOW)
        if 'v12_strategy' in strategy_data:
            v12 = strategy_data['v12_strategy']
            manipulation_score = v12.get('manipulation_score', 0)

            # Color code based on manipulation score
            if manipulation_score > 5:
                color = "🔴"
                status = "HIGH MANIPULATION"
            elif manipulation_score > 2:
                color = "🟡"
                status = "MODERATE MANIPULATION"
            else:
                color = "🟢"
                status = "LOW MANIPULATION"

            st.markdown(f"""
            **V12 Strategy (Full ZANFLOW)**
            - {color} Manipulation Score: {manipulation_score:.2f}%
            - Status: {status}
            - Inducement Rate: {v12.get('inducement_rate', 0):.2f}%
            - Market Complexity: {v12.get('market_complexity', 'N/A')}
            """)

    # Look for traditional trade setups
    if "trade_setups" in json_data:
        st.subheader("📋 Active Trade Setups")
        setups = json_data["trade_setups"]

        for i, setup in enumerate(setups):
            # Enhanced setup card with more details
            targets_raw = setup.get("targets") or setup.get("Targets", "")
            if isinstance(targets_raw, str):
                targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
            else:
                targets = targets_raw or []

            confidence = setup.get("confidence", setup.get("Confidence", "—"))
            risk_reward = setup.get("rr", setup.get("RR", "—"))

            # Determine card color based on confidence
            if confidence != "—":
                try:
                    conf_val = float(str(confidence).replace('%', ''))
                    if conf_val >= 80:
                        card_color = "#4CAF50"  # Green
                    elif conf_val >= 60:
                        card_color = "#FF9800"  # Orange
                    else:
                        card_color = "#f44336"  # Red
                except:
                    card_color = "#2196F3"  # Blue default
            else:
                card_color = "#2196F3"

            st.markdown(f"""
            <div style='border-left: 8px solid {card_color}; padding: 1em; margin: 0.5em 0; 
                        background: rgba(255,255,255,0.05); border-radius: 8px;'>
                <h4 style='margin: 0; color: {card_color};'>
                    {setup.get("name", setup.get("Name", f"Setup {i+1}"))}
                </h4>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 10px;'>
                    <div><strong>Entry:</strong> {setup.get("entry", setup.get("Entry", "—"))}</div>
                    <div><strong>Stop:</strong> {setup.get("stop", setup.get("Stop", "—"))}</div>
                    <div><strong>Risk/Reward:</strong> {risk_reward}</div>
                    <div><strong>Confidence:</strong> {confidence}</div>
                </div>
                {f"<div style='margin-top: 10px;'><strong>Targets:</strong> {', '.join(targets)}</div>" if targets else ""}
                <div style='margin-top: 10px; font-size: 0.9em; opacity: 0.8;'>
                    <strong>Status:</strong> {setup.get("status", setup.get("Status", "Pending"))}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ZANFLOW specific analysis
    if 'zanflow_analysis' in json_data:
        zanflow = json_data['zanflow_analysis']

        st.subheader("🧬 ZANFLOW Microstructure Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            manip_score = zanflow.get('manipulation_score', 0)
            st.metric("Manipulation Events", manip_score)

        with col2:
            smc_data = zanflow.get('smc_analysis', {})
            total_fvgs = smc_data.get('bullish_fvgs', 0) + smc_data.get('bearish_fvgs', 0)
            st.metric("Fair Value Gaps", total_fvgs)

        with col3:
            inducement = zanflow.get('inducement_data', {})
            total_inducements = inducement.get('high', 0) + inducement.get('low', 0)
            st.metric("Inducement Events", total_inducements)

# ====
# ENHANCED TIME RANGE FILTER WITH JSON SUPPORT
# ====
def create_time_range_filter():
    """Create enhanced time range filter"""
    st.sidebar.markdown("### ⏰ Time Range Filter")

    # Auto-detect available date range from JSON if possible
    today = date.today()

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=today - timedelta(days=7))
        start_time = st.time_input("Start Time", value=datetime.now().replace(hour=8, minute=0).time())

    with col2:
        end_date = st.date_input("End Date", value=today)
        end_time = st.time_input("End Time", value=datetime.now().replace(hour=17, minute=0).time())

    # Combine date and time
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    return start_datetime, end_datetime

# ====
# MAIN APPLICATION WITH JSON INTEGRATION
# ====
def main():
    """Enhanced main application with JSON auto-loading"""

    # Apply custom styling

    # Header with JSON status
    st.markdown("""
    <div class="header-style">
        <h1>📊 Enhanced Wyckoff VSA Analysis Dashboard v4.0</h1>
        <p><strong>Professional Volume Spread Analysis & Market Structure with JSON Integration</strong></p>
        <p>QRT-Level Advanced Trading Analytics + ZANFLOW Microstructure</p>
    </div>
    """, unsafe_allow_html=True)

    # ====
    # SIDEBAR WITH ENHANCED DATA SELECTION
    # ====
    with st.sidebar:
        st.header("🗂️ Enhanced Data Selection")

        # Parquet data selection (existing logic)
        DATA_DIR = st.secrets.get("PARQUET_DATA_DIR", "./data")
        parquet_files = list_parquet_files(DATA_DIR)
        relative_files = [f.relative_to(DATA_DIR) for f in parquet_files]

        file_info = []
        for f in relative_files:
            parts = f.stem.split("_")
            if len(parts) >= 2:
                symbol = parts[0]
                tf = parts[1]
                file_info.append((symbol, tf, f))

        symbols = sorted(set([s for s, _, _ in file_info]))
        if not symbols:
            st.warning("No symbols found in the data directory.")
            st.stop()

        selected_symbol = st.selectbox("Select Symbol", symbols)

        # Continue with existing timeframe selection
        timeframes = sorted(set([tf for s, tf, _ in file_info if s == selected_symbol]))
        if not timeframes:
            st.warning("No timeframes found for the selected symbol.")
            st.stop()
        selected_tf = st.selectbox("Select Timeframe", timeframes)

        try:
            selected_file = next(f for s, tf, f in file_info if s == selected_symbol and tf == selected_tf)
            selected_file = str(selected_file)
        except StopIteration:
            st.warning("No file found for the selected symbol and timeframe.")
            st.stop()

        # Auto-load JSON analysis
        json_dir = st.secrets.get("JSONdir", "./midas_analysis")
        comprehensive_json, comp_file = load_comprehensive_json(selected_symbol, json_dir)
        zanflow_json, zanflow_file = load_zanflow_json(selected_symbol, json_dir)
        if comprehensive_json or zanflow_json:
            json_status = "✅ JSON data loaded"
            if comprehensive_json:
                st.success(f"📄 Comprehensive: {comp_file}")
            if zanflow_json:
                st.success(f"🧬 ZANFLOW: {zanflow_file}")
        else:
            json_status = "⚠️ No JSON found"
        st.markdown(f"**JSON Status:** {json_status}")

        # Enhanced time range filter
        start_datetime, end_datetime = create_time_range_filter()

        # Bars to analyze
        max_bars = len(pd.read_parquet(Path(DATA_DIR) / selected_file))
        bars_to_use = st.slider("Last N Bars to Analyze", min_value=20, max_value=max_bars, value=min(500, max_bars), step=10)

        # Analysis options
        st.subheader("Analysis Options")
        show_phases = st.checkbox("Show Wyckoff Phases", value=True)
        show_events = st.checkbox("Show Wyckoff Events", value=True)
        show_vsa = st.checkbox("Show VSA Signals", value=True)
        show_effort_result = st.checkbox("Show Effort vs Result", value=True)
        show_json_insights = bool(comprehensive_json or zanflow_json)
        show_tfactor = st.checkbox("Compute T-Factor", value=True)

        with st.expander("Advanced Settings"):
            volume_threshold = st.slider("Volume Spike Threshold", 1.5, 3.0, 2.0, 0.1)
            volatility_threshold = st.slider("Volatility Threshold", 0.2, 1.0, 0.3, 0.1)
            phase_sensitivity = st.slider("Phase Detection Sensitivity", 0.5, 2.0, 1.0, 0.1)

    # ====
    # MAIN ANALYSIS SECTION
    # ====
    if st.button("🚀 Run Enhanced Analysis", type="primary"):
        with st.spinner("Loading market data and performing enhanced analysis..."):
            # Load parquet data
            df = load_parquet_data(DATA_DIR, selected_file)
            df = df.tail(bars_to_use)

            if df.empty:
                st.error("Unable to load data from the selected Parquet file.")
                return

            # Apply time filter if specified
            if 'datetime' in df.columns or 'timestamp' in df.columns:
                time_col = 'datetime' if 'datetime' in df.columns else 'timestamp'
                df[time_col] = pd.to_datetime(df[time_col])
                # Drop timezone info for comparison if present
                if df[time_col].dtype.tz is not None:
                    df[time_col] = df[time_col].dt.tz_convert(None)
                mask = (df[time_col] >= pd.Timestamp(start_datetime)) & (df[time_col] <= pd.Timestamp(end_datetime))
                df = df.loc[mask]

                if df.empty:
                    st.warning("No data found in the specified time range.")
                    return

            # Merge JSON insights
            merged_json = merge_json_insights(comprehensive_json, zanflow_json)

            # Perform Wyckoff analysis
            analyzer = WyckoffAnalyzer()
            analysis = analyzer.analyze(df)

            if not analysis:
                st.error("Analysis failed. Please try again.")
                return

            # Enhanced key metrics with JSON data
            st.subheader("📈 Enhanced Key Metrics")

            col1, col2, col3, col4, col5, col6 = st.columns(6)

            with col1:
                current_price = df['close'].iloc[-1]
                price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                st.metric("Current Price", f"${current_price:.2f}", f"{price_change:+.2f}%")

            with col2:
                avg_volume = df['volume'].mean()
                recent_volume = df['volume'].iloc[-5:].mean()
                volume_change = ((recent_volume - avg_volume) / avg_volume) * 100
                st.metric("Avg Volume", f"{avg_volume:,.0f}", f"{volume_change:+.1f}%")

            with col3:
                if 'trend_analysis' in analysis:
                    trend = analysis['trend_analysis']['trend']
                    st.metric("Market Trend", trend)
                else:
                    st.metric("Market Trend", "N/A")

            with col4:
                if merged_json and 'zanflow_analysis' in merged_json:
                    manip_score = merged_json['zanflow_analysis'].get('manipulation_score', 0)
                    st.metric("Manipulation Score", f"{manip_score:.1f}%")
                else:
                    st.metric("Manipulation Score", "N/A")

            with col5:
                co_activity = analysis.get('composite_operator', {}).get('institutional_activity', "N/A")
                st.metric("Institutional Activity", co_activity)

            with col6:
                t_factor = analysis.get('t_factor', "N/A")
                st.metric("T-Factor", t_factor)

            # Main analysis chart
            st.subheader("📊 Enhanced Wyckoff Analysis Chart")
            main_chart = create_wyckoff_chart(df, analysis, selected_symbol)
            st.plotly_chart(main_chart, use_container_width=True)

            # Enhanced trade setups with JSON integration
            st.subheader("🎯 Enhanced Trade Setups & Strategy Insights")
            render_enhanced_trade_setups(selected_symbol, merged_json)

            # JSON insights display
            if show_json_insights and merged_json:
                st.subheader("📄 JSON Analysis Insights")
                
                # Display in expandable sections
                if 'summary' in merged_json:
                    with st.expander("📊 Analysis Summary"):
                        summary = merged_json['summary']
                        st.json(summary)
                
                if 'zanflow_analysis' in merged_json:
                    with st.expander("🧬 ZANFLOW Microstructure"):
                        zanflow = merged_json['zanflow_analysis']
                        st.json(zanflow)

            # Continue with existing analysis sections...
            # (Phase distribution, composite operator gauge, detailed analysis, etc.)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: #888;">
        <p><strong>Enhanced Wyckoff VSA Analysis Dashboard v4.0</strong></p>
        <p>Professional-grade market analysis with JSON integration for institutional traders</p>
        <p>Built with advanced Volume Spread Analysis, Wyckoff Method principles, and ZANFLOW microstructure</p>
    </div>
    """, unsafe_allow_html=True)

# Include all your existing helper functions (create_wyckoff_chart, list_parquet_files, etc.)
# ... [Rest of your existing functions remain the same]

if __name__ == "__main__":
    main()