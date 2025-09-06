import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import importlib.util
import sys
import os
from pathlib import Path

# Page config
st.set_page_config(page_title="Tick Microstructure Dashboard", layout="wide")

# Dynamic module loading
@st.cache_resource
def load_modules():
    """Load analysis modules dynamically"""
    modules = {}
    module_paths = {
        'ncOS': 'ncOS_ultimate_microstructure_analyzer_DEFAULTS.py',
        'zanflow': 'zanflow_microstructure_analyzer.py'
    }

    for name, path in module_paths.items():
        if os.path.exists(path):
            try:
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[name] = module
                st.sidebar.success(f"✅ {name} loaded")
            except Exception as e:
                st.sidebar.error(f"❌ {name}: {str(e)[:50]}...")

    return modules

# Load data
@st.cache_data
def load_data(file_path):
    """Load tick or OHLC data"""
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
    elif file_path.endswith('.parquet'):
        df = pd.read_parquet(file_path)
    else:
        return pd.DataFrame()

    # Calculate basic metrics if needed
    if 'bid' in df.columns and 'ask' in df.columns:
        df['spread'] = df['ask'] - df['bid']
        df['mid_price'] = (df['bid'] + df['ask']) / 2

    return df

# Quick manipulation detection
def detect_manipulation(df):
    """Simple manipulation detection"""
    results = {'spoofing': [], 'wash_trading': [], 'anomalies': []}

    if 'spread' in df.columns and 'volume' in df.columns:
        # Spoofing: wide spreads with low volume
        spread_mean = df['spread'].mean()
        spread_std = df['spread'].std()
        volume_mean = df['volume'].mean()

        spoofing_mask = (df['spread'] > spread_mean + 2*spread_std) & (df['volume'] < volume_mean * 0.2)
        results['spoofing'] = df[spoofing_mask].index.tolist()

        # Wash trading: high volume with minimal price movement
        if 'mid_price' in df.columns:
            price_change = df['mid_price'].pct_change().abs()
            wash_mask = (df['volume'] > volume_mean * 3) & (price_change < 0.0001)
            results['wash_trading'] = df[wash_mask].index.tolist()

    return results

# Main app
def main():
    st.title("🎯 Tick Manipulation & Microstructure Dashboard")

    # Load modules
    modules = load_modules()

    # Sidebar
    st.sidebar.header("Configuration")

    # File selection
    files = {
        'Tick Data': 'XAUUSD_tick.csv',
        'Enriched Tick': 'Enriched_Tick_Data.csv',
        '5min Data': 'XAUUSD_5min.parquet',
        'Daily Data': 'XAUUSD_1d.parquet'
    }

    selected_file = st.sidebar.selectbox("Select Data", list(files.keys()))
    file_path = files[selected_file]

    # Load data
    if os.path.exists(file_path):
        df = load_data(file_path)

        if not df.empty:
            # Time filter
            if hasattr(df.index, 'min'):
                start = st.sidebar.slider(
                    "Start", 
                    min_value=0, 
                    max_value=len(df)-1, 
                    value=max(0, len(df)-1000)
                )
                df = df.iloc[start:]

            # Tabs
            tab1, tab2, tab3 = st.tabs(["📊 Overview", "🎯 Manipulation", "🧠 Advanced"])

            with tab1:
                # Metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Records", f"{len(df):,}")

                with col2:
                    if 'spread' in df.columns:
                        st.metric("Avg Spread", f"{df['spread'].mean():.4f}")

                with col3:
                    if 'volume' in df.columns:
                        st.metric("Total Volume", f"{df['volume'].sum():,.0f}")

                with col4:
                    if 'buy_pressure' in df.columns:
                        st.metric("Buy Pressure", f"{df['buy_pressure'].mean():.2%}")

                # Main chart
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                   row_heights=[0.7, 0.3])

                # Price
                if 'bid' in df.columns and 'ask' in df.columns:
                    fig.add_trace(go.Scatter(x=df.index, y=df['bid'], 
                                           name='Bid', line=dict(color='green')), 
                                row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['ask'], 
                                           name='Ask', line=dict(color='red')), 
                                row=1, col=1)
                elif 'close' in df.columns:
                    fig.add_trace(go.Scatter(x=df.index, y=df['close'], 
                                           name='Close'), row=1, col=1)

                # Volume
                if 'volume' in df.columns:
                    fig.add_trace(go.Bar(x=df.index, y=df['volume'], 
                                       name='Volume'), row=2, col=1)

                fig.update_layout(height=600, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.header("Manipulation Detection")

                # Run detection
                manipulation = detect_manipulation(df)

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Spoofing Events", len(manipulation['spoofing']))
                    if manipulation['spoofing']:
                        st.warning(f"Found {len(manipulation['spoofing'])} spoofing events")

                with col2:
                    st.metric("Wash Trading", len(manipulation['wash_trading']))
                    if manipulation['wash_trading']:
                        st.warning(f"Found {len(manipulation['wash_trading'])} wash trades")

                # Visualization
                if manipulation['spoofing'] or manipulation['wash_trading']:
                    fig = go.Figure()

                    if 'mid_price' in df.columns:
                        fig.add_trace(go.Scatter(x=df.index, y=df['mid_price'], 
                                               name='Price', line=dict(color='blue')))

                        # Mark spoofing
                        if manipulation['spoofing']:
                            spoof_times = manipulation['spoofing']
                            spoof_prices = df.loc[spoof_times, 'mid_price']
                            fig.add_trace(go.Scatter(x=spoof_times, y=spoof_prices,
                                                   mode='markers', name='Spoofing',
                                                   marker=dict(color='red', size=10)))

                        # Mark wash trading
                        if manipulation['wash_trading']:
                            wash_times = manipulation['wash_trading']
                            wash_prices = df.loc[wash_times, 'mid_price']
                            fig.add_trace(go.Scatter(x=wash_times, y=wash_prices,
                                                   mode='markers', name='Wash Trading',
                                                   marker=dict(color='orange', size=10)))

                    fig.update_layout(height=400, title="Manipulation Events")
                    st.plotly_chart(fig, use_container_width=True)

            with tab3:
                st.header("Advanced Analysis")

                # Use loaded modules
                if 'ncOS' in modules:
                    st.subheader("Smart Money Concepts")

                    if st.button("Run SMC Analysis"):
                        with st.spinner("Analyzing..."):
                            try:
                                smc = modules['ncOS'].SMCAnalyzer()
                                if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                                    results = smc.analyze_smc(df)

                                    # Display results
                                    if 'market_structure' in results:
                                        st.json({
                                            'trend': results['market_structure'].get('trend'),
                                            'liquidity_zones': len(results.get('liquidity_zones', [])),
                                            'order_blocks': len(results.get('order_blocks', [])),
                                            'fair_value_gaps': len(results.get('fair_value_gaps', []))
                                        })
                                else:
                                    st.error("OHLC data required for SMC analysis")
                            except Exception as e:
                                st.error(f"Error: {e}")

                if 'zanflow' in modules:
                    st.subheader("Zanflow Analysis")
                    if st.button("Run Zanflow"):
                        st.info("Ready to integrate Zanflow analyzer")

                # Export section
                st.subheader("Export for LLM Analysis")

                export_data = {
                    'timestamp': df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
                    'records': len(df),
                    'manipulation_events': {
                        'spoofing': len(manipulation['spoofing']),
                        'wash_trading': len(manipulation['wash_trading'])
                    }
                }

                if 'spread' in df.columns:
                    export_data['spread_stats'] = {
                        'mean': float(df['spread'].mean()),
                        'std': float(df['spread'].std()),
                        'max': float(df['spread'].max())
                    }

                col1, col2 = st.columns(2)

                with col1:
                    st.json(export_data)

                with col2:
                    st.text_area("LLM Prompt Template", 
                                value="Analyze this microstructure data and identify trading opportunities...")
        else:
            st.error(f"Could not load {file_path}")
    else:
        st.error(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
