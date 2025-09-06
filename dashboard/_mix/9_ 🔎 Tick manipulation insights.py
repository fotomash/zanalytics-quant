def load_comprehensive_json(symbol, json_dir=None):
    """Load comprehensive JSON analysis for a symbol"""
    if json_dir is None:
        json_dir = st.secrets.get("JSONdir", "./midas_analysis")
    json_path = Path(f"{json_dir}/{symbol}_comprehensive.json")
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
                else:
                    st.warning(f"Comprehensive JSON file '{json_path}' is empty.")
                    return None
        except Exception as e:
            st.warning(f"Could not parse comprehensive JSON: {e}")
            return None
    else:
        return None

def render_trade_setups(symbol, json_data):
    """Render trade setups from JSON data"""
    if json_data and "trade_setups" in json_data:
        setups = json_data["trade_setups"]
        for setup in setups:
            with st.container():
                st.markdown(
                    f"<div style='border-left:8px solid {setup.get('color', '#ffc13b')};padding:0.7em 1em;"
                    f"margin:0.5em 0;background:rgba(80,80,80,0.1);border-radius:8px'>"
                    f"<b>{setup.get('name', 'Unnamed Setup')}</b> | "
                    f"<b>Entry:</b> {setup.get('entry', '—')} | "
                    f"<b>Stop:</b> {setup.get('stop', '—')} | "
                    f"<b>RR:</b> {setup.get('risk_reward', '—')} | "
                    f"<b>Status:</b> {setup.get('status', 'Pending')}"
                    f"</div>", unsafe_allow_html=True
                )
    else:
        st.info("No trade setups found in JSON data")
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import json
import sys
import os
from pathlib import Path
import importlib.util
import warnings

# --- Streamlit version compatibility ---------------------------------
if hasattr(st, "cache_data"):
    cache_data = st.cache_data
else:  # Fallback for older Streamlit versions
    cache_data = st.cache

if hasattr(st, "cache_resource"):
    cache_resource = st.cache_resource
else:  # Fallback for older Streamlit versions
    cache_resource = st.cache
# ----------------------------------------------------------------------

warnings.filterwarnings('ignore')

# Configure page
st.set_page_config(
    page_title="Xanalytics Microstructure Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {padding: 0rem 1rem;}
    .stMetric {background-color: #f0f2f6; padding: 10px; border-radius: 5px;}
    .plot-container {border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px;}
    div[data-testid="metric-container"] {background-color: #f8f9fa; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)


# ==================== MODULE LOADING ====================
@cache_resource
def load_analyzer_modules():
    """Dynamically load analyzer modules"""
    modules = {}

    # Try to load zanflow analyzer
    try:
        spec = importlib.util.spec_from_file_location(
            "zanflow_analyzer",
            "utils/zanflow_microstructure_analyzer.py"
        )
        if spec and spec.loader:
            zanflow_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(zanflow_module)
            modules['zanflow'] = zanflow_module
            st.sidebar.success("✅ Zanflow Analyzer loaded")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Zanflow Analyzer not loaded: {str(e)[:50]}...")
        st.sidebar.warning(f"⚠️ Zanflow Analyzer not loaded: {str(e)[:50]}...")

    return modules


# Load modules
modules = load_analyzer_modules()


# ==================== DATA LOADING ====================
@cache_data
def load_tick_data(file_path):
    """Load tick data with proper parsing"""
    try:
        df = pd.read_csv(file_path)

        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

        # Ensure numeric columns
        numeric_cols = ['bid', 'ask', 'spread', 'volume', 'real_volume',
                        'inferred_volume', 'buy_pressure', 'mid_price']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


@cache_data
def load_parquet_data(file_path):
    """Load parquet data"""
    try:
        df = pd.read_parquet(file_path)
        if 'timestamp' in df.columns and df.index.name != 'timestamp':
            df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading parquet: {e}")
        return pd.DataFrame()


# ==================== ANALYSIS FUNCTIONS ====================
def analyze_tick_manipulation(df):
    """Analyze tick data for manipulation patterns"""
    results = {
        'spoofing_events': [],
        'layering_events': [],
        'wash_trading': [],
        'momentum_ignition': [],
        'quote_stuffing': {}
    }

    if len(df) < 10:
        return results

    # Spoofing detection
    if 'bid' in df.columns and 'ask' in df.columns:
        bid_changes = df['bid'].diff().abs()
        ask_changes = df['ask'].diff().abs()
        volume = df.get('volume', pd.Series(1, index=df.index))

        # Large price changes with low/zero volume
        spoofing_threshold = bid_changes.std() * 2
        potential_spoofs = df[
            ((bid_changes > spoofing_threshold) | (ask_changes > spoofing_threshold)) &
            (volume < volume.mean() * 0.1)
            ]

        for idx, row in potential_spoofs.iterrows():
            results['spoofing_events'].append({
                'timestamp': idx,
                'bid': row.get('bid', 0),
                'ask': row.get('ask', 0),
                'volume': row.get('volume', 0),
                'severity': max(bid_changes.loc[idx], ask_changes.loc[idx]) / spoofing_threshold
            })

    # Wash trading detection
    if 'volume' in df.columns and 'mid_price' in df.columns:
        # High volume with minimal price movement
        rolling_vol = df['volume'].rolling(10).sum()
        price_range = df['mid_price'].rolling(10).apply(lambda x: x.max() - x.min())

        wash_candidates = df[
            (rolling_vol > rolling_vol.mean() * 3) &
            (price_range < df['mid_price'].mean() * 0.001)
            ]

        for idx, row in wash_candidates.iterrows():
            results['wash_trading'].append({
                'timestamp': idx,
                'volume': rolling_vol.loc[idx],
                'price_range': price_range.loc[idx],
                'suspicion_score': rolling_vol.loc[idx] / (price_range.loc[idx] + 1e-10)
            })

    # Quote stuffing metrics
    if len(df) > 1:
        time_diffs = df.index.to_series().diff().dt.total_seconds()
        rapid_quotes = (time_diffs < 0.001).sum()

        results['quote_stuffing'] = {
            'total_quotes': len(df),
            'rapid_quotes': int(rapid_quotes),
            'rapid_quote_ratio': rapid_quotes / len(df),
            'mean_time_between_quotes': time_diffs.mean(),
            'stuffing_suspected': rapid_quotes > len(df) * 0.1
        }

    return results


def calculate_microstructure_metrics(df):
    """Calculate comprehensive microstructure metrics"""
    metrics = {}

    if 'bid' in df.columns and 'ask' in df.columns:
        # Spread metrics
        df['spread'] = df['ask'] - df['bid']
        metrics['avg_spread'] = df['spread'].mean()
        metrics['spread_volatility'] = df['spread'].std()
        metrics['max_spread'] = df['spread'].max()

        # Mid price
        df['mid_price'] = (df['bid'] + df['ask']) / 2

        # Price impact
        if len(df) > 1:
            df['price_impact'] = df['mid_price'].diff().abs()
            metrics['avg_price_impact'] = df['price_impact'].mean()

    if 'volume' in df.columns:
        metrics['total_volume'] = df['volume'].sum()
        metrics['avg_volume'] = df['volume'].mean()
        metrics['volume_volatility'] = df['volume'].std()

    # Order flow imbalance
    if 'buy_pressure' in df.columns:
        metrics['avg_buy_pressure'] = df['buy_pressure'].mean()
        metrics['order_flow_imbalance'] = (df['buy_pressure'] - 0.5).mean()

    return metrics


# ==================== VISUALIZATION FUNCTIONS ====================
def create_tick_manipulation_chart(df, manipulation_results):
    """Create interactive chart showing manipulation patterns"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=('Price & Spread', 'Volume & Manipulation Events', 'Order Flow'),
        row_heights=[0.4, 0.3, 0.3]
    )

    # Price and spread
    if 'bid' in df.columns and 'ask' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['bid'], name='Bid',
                       line=dict(color='green', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['ask'], name='Ask',
                       line=dict(color='red', width=1)),
            row=1, col=1
        )

        if 'mid_price' in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df['mid_price'], name='Mid Price',
                           line=dict(color='blue', width=2)),
                row=1, col=1
            )

    # Volume with manipulation markers
    if 'volume' in df.columns:
        fig.add_trace(
            go.Bar(x=df.index, y=df['volume'], name='Volume',
                   marker_color='lightblue'),
            row=2, col=1
        )

    # Add spoofing events
    if manipulation_results['spoofing_events']:
        spoofing_times = [e['timestamp'] for e in manipulation_results['spoofing_events']]
        spoofing_prices = [df.loc[e['timestamp'], 'mid_price'] if 'mid_price' in df.columns else 0
                           for e in manipulation_results['spoofing_events']]

        fig.add_trace(
            go.Scatter(x=spoofing_times, y=spoofing_prices,
                       mode='markers', name='Spoofing',
                       marker=dict(color='red', size=10, symbol='x')),
            row=1, col=1
        )

    # Order flow
    if 'buy_pressure' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['buy_pressure'], name='Buy Pressure',
                       line=dict(color='green'), fill='tozeroy'),
            row=3, col=1
        )

        # Add 0.5 reference line
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray", row=3, col=1)

    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='x unified'
    )

    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="Buy Pressure", row=3, col=1)

    return fig


def create_microstructure_heatmap(df):
    """Create heatmap of microstructure patterns"""
    # Prepare data for heatmap
    if len(df) > 100:
        # Resample to manageable size
        df_resampled = df.resample('1min').agg({
            'spread': 'mean',
            'volume': 'sum',
            'buy_pressure': 'mean'
        }).dropna()
    else:
        df_resampled = df

    # Create correlation matrix
    corr_cols = []
    for col in ['spread', 'volume', 'buy_pressure', 'price_impact']:
        if col in df_resampled.columns:
            corr_cols.append(col)

    if len(corr_cols) > 1:
        corr_matrix = df_resampled[corr_cols].corr()

        fig = px.imshow(corr_matrix,
                        labels=dict(color="Correlation"),
                        x=corr_cols,
                        y=corr_cols,
                        color_continuous_scale='RdBu_r',
                        aspect="auto")

        fig.update_layout(
            title="Microstructure Correlation Matrix",
            height=400
        )

        return fig
    else:
        return None


# ==================== MAIN DASHBOARD ====================
def main():
    st.title("🎯 Xanalytics Unified Microstructure Dashboard")
    st.markdown("### Advanced Tick Manipulation & Market Microstructure Analysis")

    # Sidebar configuration
    # --- Unified Data Selection Sidebar ---
    from pathlib import Path

    st.sidebar.header("📁 Data Selection")

    parquet_dir = Path(st.secrets["PARQUET_DATA_DIR"])
    tick_dir = Path(st.secrets["tick_data_enriched"])

    # Unified pairs: intersection of pairs present in both directories
    candles_pairs = {f.name for f in parquet_dir.iterdir() if f.is_dir()}
    ticks_pairs = {f.name for f in tick_dir.iterdir() if f.is_dir()}
    available_pairs = sorted(candles_pairs & ticks_pairs)
    selected_pair = st.sidebar.selectbox(
        "💱 Select Pair", available_pairs, index=0 if available_pairs else None, key="unified_pair"
    )
    preferred_timeframes = ["1min", "3min", "5min", "15min", "30min", "1h", "4h", "1d"]

    # JSON auto-load toggle
    enable_json = st.sidebar.checkbox("Auto-load JSON Analysis", value=True)

    comprehensive_json = None
    if selected_pair and enable_json:
        comprehensive_json = load_comprehensive_json(selected_pair)
        if comprehensive_json:
            st.sidebar.success(f"✅ Loaded JSON analysis for {selected_pair}")
        else:
            st.sidebar.info(f"ℹ️ No JSON analysis found for {selected_pair}")

    # Candles timeframes (per selected pair)
    candles_timeframes = []
    candles_timeframe_map = {}
    if selected_pair:
        pair_dir = parquet_dir / selected_pair
        files = {f.stem for f in pair_dir.glob("*.parquet")}
        candles_timeframes = [tf for tf in preferred_timeframes if tf in files]
        for tf in candles_timeframes:
            candles_timeframe_map[tf] = pair_dir / f"{tf}.parquet"
    selected_candles_timeframe = st.sidebar.selectbox(
        "📊 Candle Timeframe", candles_timeframes, disabled=not candles_timeframes, key="candles_timeframe"
    )

    # Tick timeframes (per selected pair)
    ticks_timeframes = []
    ticks_timeframe_map = {}
    if selected_pair:
        pair_dir = tick_dir / selected_pair
        files = {f.stem for f in pair_dir.glob("*.parquet")}
        # Add board timeframes if present
        ticks_timeframes = [tf for tf in preferred_timeframes if tf in files]
        for tf in ticks_timeframes:
            ticks_timeframe_map[tf] = pair_dir / f"{tf}.parquet"
        # Support _tick.parquet as "Raw Tick"
        tick_file = pair_dir / f"{selected_pair}_tick.parquet"
        if tick_file.exists():
            ticks_timeframes.append("Raw Tick")
            ticks_timeframe_map["Raw Tick"] = tick_file
    selected_ticks_timeframe = st.sidebar.selectbox(
        "🕒 Tick Timeframe", ticks_timeframes, disabled=not ticks_timeframes, key="tick_timeframe_board"
    )

    # --- Data Loading Logic ---
    # Try to load based on sidebar selections above
    df = pd.DataFrame()
    data_source = None
    # Priority: Candles (Parquet) if both pair and timeframe selected, else Tick Data if both selected
    if selected_pair and selected_candles_timeframe:
        file_path = candles_timeframe_map.get(selected_candles_timeframe)
        if file_path and file_path.exists():
            df = load_parquet_data(file_path)
            data_source = f"{selected_pair} {selected_candles_timeframe} (Candles)"
    elif selected_pair and selected_ticks_timeframe:
        file_path = ticks_timeframe_map.get(selected_ticks_timeframe)
        if file_path:
            # Handle "Raw Tick" option
            if selected_ticks_timeframe == "Raw Tick":
                df = load_parquet_data(file_path)
            elif file_path.suffix == ".csv":
                df = load_tick_data(file_path)
            else:
                df = load_parquet_data(file_path)
            data_source = f"{selected_pair} {selected_ticks_timeframe} (Ticks)"

    # If nothing loaded, allow upload as fallback
    if df.empty:
        st.sidebar.markdown("---")
        st.sidebar.markdown("#### 📤 Or Upload File")
        uploaded_file = st.sidebar.file_uploader(
            "Choose a file",
            type=['csv', 'parquet', 'json']
        )
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                df = load_tick_data(uploaded_file)
                data_source = uploaded_file.name
            elif uploaded_file.name.endswith('.parquet'):
                df = load_parquet_data(uploaded_file)
                data_source = uploaded_file.name

    if df.empty:
        st.warning("⚠️ No data loaded. Please select or upload a data file.")
        return

    # Time range filter
    st.sidebar.header("⏰ Time Range Filter")
    if hasattr(df.index, 'min'):
        min_datetime = df.index.min()
        max_datetime = df.index.max()
        # Sidebar datetime selectors
        start_date = st.sidebar.date_input(
            "Start Date", value=min_datetime.date(), min_value=min_datetime.date(), max_value=max_datetime.date()
        )
        start_time_val = st.sidebar.time_input(
            "Start Time", value=min_datetime.time()
        )
        end_date = st.sidebar.date_input(
            "End Date", value=max_datetime.date(), min_value=min_datetime.date(), max_value=max_datetime.date()
        )
        end_time_val = st.sidebar.time_input(
            "End Time", value=max_datetime.time()
        )
        from datetime import datetime as dt
        start_time = dt.combine(start_date, start_time_val)
        end_time = dt.combine(end_date, end_time_val)

        # --- Timezone-awareness fix ---
        if hasattr(df.index, "tz") and df.index.tz is not None:
            # Convert to pandas.Timestamp with correct tz-awareness
            try:
                start_time = pd.Timestamp(start_time).tz_convert(df.index.tz)
                end_time = pd.Timestamp(end_time).tz_convert(df.index.tz)
            except TypeError:
                start_time = pd.Timestamp(start_time).tz_localize(df.index.tz)
                end_time = pd.Timestamp(end_time).tz_localize(df.index.tz)
        # Filter data
        df = df.loc[start_time:end_time]

    # Analysis options
    st.sidebar.header("🔧 Analysis Options")
    enable_manipulation = st.sidebar.checkbox("Manipulation Detection", True)
    enable_smc = st.sidebar.checkbox("Smart Money Concepts", True)
    enable_wyckoff = st.sidebar.checkbox("Wyckoff Analysis", False)
    enable_ml = st.sidebar.checkbox("ML Predictions", False)

    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🎯 Manipulation Analysis",
        "📈 Microstructure Metrics",
        "🧠 Advanced Analytics",
        "📤 Export & Integration"
    ])

    # Tab 1: Overview
    with tab1:
        st.header("Market Overview")
        if data_source:
            st.caption(f"**Data Source:** {data_source}")

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        metrics = calculate_microstructure_metrics(df)

        with col1:
            st.metric(
                "Total Records",
                f"{len(df):,}",
                delta=f"{len(df) / 1000:.1f}K rows"
            )

        with col2:
            if 'avg_spread' in metrics:
                st.metric(
                    "Average Spread",
                    f"{metrics['avg_spread']:.4f}",
                    delta=f"±{metrics.get('spread_volatility', 0):.4f}"
                )

        with col3:
            if 'total_volume' in metrics:
                st.metric(
                    "Total Volume",
                    f"{metrics['total_volume']:,.0f}",
                    delta=f"Avg: {metrics['avg_volume']:.1f}"
                )

        with col4:
            if 'avg_buy_pressure' in metrics:
                st.metric(
                    "Buy Pressure",
                    f"{metrics['avg_buy_pressure']:.2%}",
                    delta=f"Imbalance: {metrics.get('order_flow_imbalance', 0):.3f}"
                )

        # Main chart
        st.subheader("Price Action & Microstructure")

        if enable_manipulation:
            manipulation_results = analyze_tick_manipulation(df)
            fig = create_tick_manipulation_chart(df, manipulation_results)
        else:
            # Simple price chart
            fig = go.Figure()
            if 'mid_price' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['mid_price'], name='Mid Price'))
            elif 'close' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['close'], name='Close'))

            fig.update_layout(height=600, hovermode='x unified')

        st.plotly_chart(fig, use_container_width=True)

        # If comprehensive_json is loaded, show trade setups (optional visualization)
        if comprehensive_json:
            st.subheader("Trade Setups (from JSON Analysis)")
            render_trade_setups(selected_pair, comprehensive_json)

    # Tab 2: Manipulation Analysis
    with tab2:
        st.header("🎯 Market Manipulation Detection")

        if enable_manipulation:
            manipulation_results = analyze_tick_manipulation(df)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Spoofing Events",
                    len(manipulation_results['spoofing_events']),
                    delta="Detected" if len(manipulation_results['spoofing_events']) > 0 else "Clean"
                )

            with col2:
                st.metric(
                    "Wash Trading",
                    len(manipulation_results['wash_trading']),
                    delta="Suspicious" if len(manipulation_results['wash_trading']) > 0 else "Normal"
                )

            with col3:
                qs = manipulation_results.get('quote_stuffing', {})
                st.metric(
                    "Quote Stuffing",
                    f"{qs.get('rapid_quote_ratio', 0):.1%}",
                    delta="High" if qs.get('stuffing_suspected', False) else "Low"
                )

            with col4:
                st.metric(
                    "Momentum Ignition",
                    len(manipulation_results.get('momentum_ignition', [])),
                    delta="Events"
                )

            # Detailed analysis
            st.subheader("Manipulation Event Details")

            if manipulation_results['spoofing_events']:
                st.write("**Spoofing Events Detected:**")
                spoofing_df = pd.DataFrame(manipulation_results['spoofing_events'])
                st.dataframe(
                    spoofing_df.style.background_gradient(subset=['severity']),
                    use_container_width=True
                )

            if manipulation_results['wash_trading']:
                st.write("**Potential Wash Trading:**")
                wash_df = pd.DataFrame(manipulation_results['wash_trading'])
                st.dataframe(
                    wash_df.style.background_gradient(subset=['suspicion_score']),
                    use_container_width=True
                )

            # Quote stuffing details
            if manipulation_results['quote_stuffing']:
                st.write("**Quote Stuffing Analysis:**")
                qs_data = manipulation_results['quote_stuffing']

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"Total Quotes: {qs_data['total_quotes']:,}")
                    st.info(f"Rapid Quotes: {qs_data['rapid_quotes']:,}")

                with col2:
                    st.info(f"Mean Time Between: {qs_data['mean_time_between_quotes']:.6f}s")
                    if qs_data['stuffing_suspected']:
                        st.error("⚠️ Quote Stuffing Suspected!")

        else:
            st.info("Enable Manipulation Detection in the sidebar to see analysis.")

    # Tab 3: Microstructure Metrics
    with tab3:
        st.header("📈 Market Microstructure Analysis")

        # Spread analysis
        if 'spread' in df.columns:
            st.subheader("Spread Dynamics")

            col1, col2 = st.columns(2)

            with col1:
                # Spread distribution
                fig_spread = px.histogram(
                    df, x='spread',
                    title="Spread Distribution",
                    nbins=50
                )
                st.plotly_chart(fig_spread, use_container_width=True)

            with col2:
                # Spread over time
                fig_spread_time = go.Figure()
                fig_spread_time.add_trace(
                    go.Scatter(x=df.index, y=df['spread'], name='Spread')
                )

                # Add rolling average
                if len(df) > 20:
                    df['spread_ma'] = df['spread'].rolling(20).mean()
                    fig_spread_time.add_trace(
                        go.Scatter(x=df.index, y=df['spread_ma'],
                                   name='20-period MA', line=dict(dash='dash'))
                    )

                fig_spread_time.update_layout(
                    title="Spread Evolution",
                    height=400
                )
                st.plotly_chart(fig_spread_time, use_container_width=True)

        # Correlation heatmap
        st.subheader("Microstructure Correlations")
        heatmap_fig = create_microstructure_heatmap(df)
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)

        # Volume profile
        if 'volume' in df.columns and 'mid_price' in df.columns:
            st.subheader("Volume Profile Analysis")

            # Create price bins
            price_bins = pd.cut(df['mid_price'], bins=30)
            volume_profile = df.groupby(price_bins)['volume'].sum().sort_index()

            fig_vp = go.Figure()
            fig_vp.add_trace(go.Bar(
                y=[str(bin) for bin in volume_profile.index],
                x=volume_profile.values,
                orientation='h',
                name='Volume'
            ))

            fig_vp.update_layout(
                title="Volume Profile",
                xaxis_title="Volume",
                yaxis_title="Price Range",
                height=600
            )

            st.plotly_chart(fig_vp, use_container_width=True)

    # Tab 4: Advanced Analytics
    with tab4:
        st.header("🧠 Advanced Analytics")

        # Use analyzer modules if available
        if 'ncOS' in modules and enable_smc:
            st.subheader("Smart Money Concepts Analysis")

            try:
                # Create SMC analyzer instance
                smc_analyzer = modules['ncOS'].SMCAnalyzer()

                # Ensure required columns
                if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                    smc_results = smc_analyzer.analyze_smc(df)

                    # Display SMC results
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Market Structure:**")
                        if 'market_structure' in smc_results:
                            ms = smc_results['market_structure']
                            st.info(f"Trend: {ms.get('trend', 'Unknown')}")
                            st.info(f"Swing Highs: {len(ms.get('swing_highs', []))}")
                            st.info(f"Swing Lows: {len(ms.get('swing_lows', []))}")

                    with col2:
                        st.write("**Liquidity Analysis:**")
                        if 'liquidity_zones' in smc_results:
                            lz = smc_results['liquidity_zones']
                            st.info(f"Liquidity Zones: {len(lz)}")

                            if lz:
                                high_zones = [z for z in lz if z['type'] == 'liquidity_high']
                                low_zones = [z for z in lz if z['type'] == 'liquidity_low']
                                st.info(f"High Zones: {len(high_zones)}")
                                st.info(f"Low Zones: {len(low_zones)}")

                    # Order blocks
                    if 'order_blocks' in smc_results and smc_results['order_blocks']:
                        st.write("**Order Blocks Detected:**")
                        ob_df = pd.DataFrame(smc_results['order_blocks'])
                        st.dataframe(ob_df, use_container_width=True)

                    # Fair value gaps
                    if 'fair_value_gaps' in smc_results and smc_results['fair_value_gaps']:
                        st.write("**Fair Value Gaps:**")
                        fvg_df = pd.DataFrame(smc_results['fair_value_gaps'])
                        st.dataframe(fvg_df, use_container_width=True)
                else:
                    st.warning("OHLC data required for SMC analysis")

            except Exception as e:
                st.error(f"Error in SMC analysis: {str(e)}")

        if 'ncOS' in modules and enable_wyckoff:
            st.subheader("Wyckoff Analysis")

            try:
                # Create Wyckoff analyzer instance
                wyckoff_analyzer = modules['ncOS'].WyckoffAnalyzer()

                if 'close' in df.columns:
                    wyckoff_results = wyckoff_analyzer.analyze_wyckoff(df)

                    # Display Wyckoff phases
                    if 'phases' in wyckoff_results and wyckoff_results['phases']:
                        st.write("**Detected Wyckoff Phases:**")
                        phases_df = pd.DataFrame(wyckoff_results['phases'])
                        st.dataframe(phases_df, use_container_width=True)

                    # Volume analysis
                    if 'volume_analysis' in wyckoff_results:
                        va = wyckoff_results['volume_analysis']
                        st.write("**Volume Analysis:**")
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Volume Trend", f"{va.get('volume_trend', 0):.4f}")
                            st.metric("Price Trend", f"{va.get('price_trend', 0):.4f}")

                        with col2:
                            divergence = "Yes" if va.get('divergence', False) else "No"
                            st.metric("Divergence", divergence)
                            st.metric("Avg Volume", f"{va.get('avg_volume', 0):,.0f}")

            except Exception as e:
                st.error(f"Error in Wyckoff analysis: {str(e)}")

        if enable_ml:
            st.subheader("Machine Learning Predictions")
            st.info("ML predictions would integrate with your custom GPT models here")

            # Placeholder for ML integration
            if st.button("Generate ML Insights"):
                with st.spinner("Analyzing patterns..."):
                    # This is where you'd integrate with your LLM/GPT system
                    st.success("Ready for LLM integration!")

                    # Sample insight structure
                    insights = {
                        "market_regime": "Accumulation Phase",
                        "manipulation_risk": "Medium",
                        "recommended_action": "Monitor for breakout",
                        "confidence": 0.75
                    }

                    st.json(insights)

    # Tab 5: Export & Integration
    with tab5:
        st.header("📤 Export & Integration")

        st.subheader("Data Export Options")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Export to CSV"):
                csv = df.to_csv()
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"microstructure_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

        with col2:
            if st.button("Export to JSON"):
                # Create comprehensive export
                export_data = {
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "records": len(df),
                        "timeframe": data_source
                    },
                    "metrics": metrics,
                    "data": df.to_dict(orient='records') if len(df) < 1000 else df.head(1000).to_dict(orient='records')
                }

                if enable_manipulation:
                    export_data["manipulation_analysis"] = manipulation_results

                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"analysis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

        with col3:
            if st.button("Generate Report"):
                st.info("Report generation ready for integration with your LLM system")

        st.subheader("LLM Integration Configuration")

        with st.expander("Configure LLM Integration"):
            endpoint = st.text_input("LLM API Endpoint", placeholder="https://your-gpt-endpoint.com/api")
            api_key = st.text_input("API Key", type="password")

            prompt_template = st.text_area(
                "Analysis Prompt Template",
                value="""Analyze the following market microstructure data:

Metrics: {metrics}
Manipulation Events: {manipulation_events}
Time Period: {time_period}

Provide insights on:
1. Market manipulation risks
2. Smart money positioning
3. Recommended trading actions
4. Risk levels"""
            )

            if st.button("Test LLM Connection"):
                if endpoint and api_key:
                    st.success("Ready to integrate with your custom GPT!")
                else:
                    st.error("Please provide endpoint and API key")

        st.subheader("Module Integration Status")

        for module_name, module in modules.items():
            st.success(f"✅ {module_name} module loaded and ready")

        # Display available functions from modules
        if modules:
            with st.expander("Available Analysis Functions"):
                for module_name, module in modules.items():
                    st.write(f"**{module_name} Functions:**")

                    # List key classes and functions
                    items = []
                    for item in dir(module):
                        if not item.startswith('_') and item[0].isupper():
                            items.append(f"- {item}")

                    st.write("\n".join(items[:10]))  # Show first 10
                    if len(items) > 10:
                        st.write(f"... and {len(items) - 10} more")


if __name__ == "__main__":
    main()