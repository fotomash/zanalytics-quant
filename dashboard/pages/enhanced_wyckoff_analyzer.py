import sys
from pathlib import Path
# ===== Add project root to sys.path so core/wyckoff modules can be imported =====
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
"""
Enhanced Wyckoff Analysis Dashboard v4.0 - Professional Quant Edition
Integrates Wyckoff Method with Microstructure Analysis and Tick Manipulation Detection
"""
import ta
from ta.volatility import BollingerBands

from core.wyckoff.unified_wyckoff_engine import UnifiedWyckoffEngine
EnhancedWyckoffAnalyzer = UnifiedWyckoffEngine

# ==== Local Dashboard Styling (copied from Home.py) ====
CHART_THEME = "plotly_dark"
BG_COLOR = "rgba(0,0,0,0.02)"
FONT_COLOR = "white"
CANDLE_UP_COLOR = "lime"
CANDLE_DOWN_COLOR = "red"
WYCKOFF_ACCUM_COLOR = "rgba(0,255,0,0.05)"
WYCKOFF_MARKUP_COLOR = "rgba(0,0,255,0.05)"
WYCKOFF_DIST_COLOR = "rgba(255,165,0,0.05)"
WYCKOFF_MARKDOWN_COLOR = "rgba(255,0,0,0.05)"

def apply_dashboard_style(fig, title=None, height=800):
    """Apply consistent dark style."""
    fig.update_layout(
        template=CHART_THEME,
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(color=FONT_COLOR),
        height=height,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    if title:
        fig.update_layout(
            title={"text": title, "x":0.5, "xanchor":"center", "yanchor":"top"}
        )
    fig.update_xaxes(showgrid=False, rangeslider_visible=False)
    fig.update_yaxes(showgrid=False)
    return fig

import streamlit as st
# === OpenAI for user prompt (added) ===
import openai
openai.api_key = st.secrets["OPENAI_API_KEY"]
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
from pathlib import Path
from datetime import datetime, timedelta
import warnings
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
from scipy import stats, signal
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

# Home.py background and panel CSS (inserted per instructions)
st.markdown("""
<style>
/* Home.py background gradient */
.main {
    background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=1400&q=80');
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
}
/* Panel container transparency */
.main .block-container {
    background-color: rgba(0,0,0,0.025) !important;
}
</style>
""", unsafe_allow_html=True)

# Configure logging
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Professional styling
st.markdown("""
<style>
/* Professional dark theme */
.main {
    background: #0e1117;
    color: #ffffff;
}

/* Header styling */
.quant-header {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    padding: 2rem;
    border-radius: 15px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

/* Metric cards */
.metric-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 1.5rem;
    border-radius: 10px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0,0,0,0.2);
}

/* Alert boxes */
.manipulation-alert {
    background: linear-gradient(45deg, #ff6b6b, #ee5a6f);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
    font-weight: 600;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 0.8; }
    50% { opacity: 1; }
    100% { opacity: 0.8; }
}

/* Chart containers */
.chart-container {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 15px;
    padding: 1.5rem;
    margin: 1rem 0;
}

/* Phase indicators */
.phase-badge {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: 600;
    margin: 0.2rem;
    font-size: 0.9rem;
}

.phase-accumulation { background: #27ae60; color: white; }
.phase-markup { background: #3498db; color: white; }
.phase-distribution { background: #e67e22; color: white; }
.phase-markdown { background: #e74c3c; color: white; }
</style>
""", unsafe_allow_html=True)


def create_institutional_activity_chart(analysis: Dict) -> go.Figure:
    """Create institutional activity visualization"""

    if 'composite_operator' not in analysis:
        return go.Figure()

    co_data = analysis['composite_operator']

    # Create gauge chart for institutional activity
    if co_data['phase'] == 'Accumulation':
        value = 75
        color = 'green'
    elif co_data['phase'] == 'Distribution':
        value = 25
        color = 'red'
    else:
        value = 50
        color = 'yellow'

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Institutional Activity", 'font': {'size': 20}},
        delta={'reference': 50, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 25], 'color': 'rgba(255,0,0,0.3)'},
                {'range': [25, 50], 'color': 'rgba(255,255,0,0.3)'},
                {'range': [50, 75], 'color': 'rgba(255,255,0,0.3)'},
                {'range': [75, 100], 'color': 'rgba(0,255,0,0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "white", 'family': "Arial"},
        height=400
    )

    return fig

def create_volume_profile_chart(df: pd.DataFrame, analysis: Dict) -> go.Figure:
    """Create volume profile visualization"""

    if 'volume_profile' not in analysis:
        return go.Figure()

    profile = analysis['volume_profile']['profile']
    poc = analysis['volume_profile']['poc']

    # Create horizontal bar chart for volume profile
    fig = go.Figure()

    # Add volume profile bars
    prices = [p['price'] for p in profile]
    volumes = [p['volume'] for p in profile]

    fig.add_trace(go.Bar(
        x=volumes,
        y=prices,
        orientation='h',
        marker=dict(
            color=volumes,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Volume")
        ),
        name='Volume Profile'
    ))

    # Add POC line
    fig.add_hline(
        y=poc,
        line_dash="dash",
        line_color="red",
        annotation_text="POC",
        annotation_position="right"
    )

    # Add value area
    fig.add_hrect(
        y0=analysis['volume_profile']['value_area_low'],
        y1=analysis['volume_profile']['value_area_high'],
        fillcolor="yellow",
        opacity=0.2,
        line_width=0,
        annotation_text="Value Area",
        annotation_position="right"
    )

    fig.update_layout(
        title="Volume Profile Analysis",
        xaxis_title="Volume",
        yaxis_title="Price",
        template='plotly_dark',
        height=600
    )

    return fig

def create_manipulation_heatmap(analysis: Dict, df: pd.DataFrame) -> go.Figure:
    """Create manipulation detection heatmap"""

    if 'manipulation_detection' not in analysis:
        return go.Figure()

    # Create time-based heatmap of manipulation events
    hours = list(range(24))
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

    # Initialize heatmap data
    z = [[0 for _ in hours] for _ in days]

    # Count manipulation events by time
    for event_type in ['stop_hunts', 'spoofing_events', 'wash_trades']:
        for event in analysis['manipulation_detection'].get(event_type, []):
            if event['index'] < len(df):
                timestamp = df.index[event['index']]
                if hasattr(timestamp, 'hour') and hasattr(timestamp, 'dayofweek'):
                    if timestamp.dayofweek < 5:  # Weekdays only
                        z[timestamp.dayofweek][timestamp.hour] += 1

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=hours,
        y=days,
        colorscale='Reds',
        hoverongaps=False,
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Events: %{z}<extra></extra>"
    ))

    fig.update_layout(
        title="Manipulation Activity Heatmap",
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        template='plotly_dark',
        height=400
    )

    return fig

def create_risk_dashboard(analysis: Dict) -> go.Figure:
    """Create comprehensive risk metrics dashboard"""

    if 'risk_metrics' not in analysis:
        return go.Figure()

    risk = analysis['risk_metrics']

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Volatility', 'Sharpe Ratio', 'Max Drawdown', 'VaR 95%'),
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}],
               [{'type': 'indicator'}, {'type': 'indicator'}]]
    )

    # Volatility gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=risk['volatility'] * 100,
        title={'text': "Annual Vol %"},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [0, 50]},
               'bar': {'color': "darkblue"},
               'steps': [
                   {'range': [0, 15], 'color': "lightgray"},
                   {'range': [15, 30], 'color': "gray"},
                   {'range': [30, 50], 'color': "lightgray"}],
               'threshold': {'line': {'color': "red", 'width': 4},
                            'thickness': 0.75, 'value': 40}}
    ), row=1, col=1)

    # Sharpe ratio
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=risk['sharpe_ratio'],
        title={'text': "Sharpe Ratio"},
        delta={'reference': 1.0, 'relative': True},
        domain={'x': [0, 1], 'y': [0, 1]}
    ), row=1, col=2)

    # Max drawdown
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=abs(risk['max_drawdown']) * 100,
        title={'text': "Max Drawdown %"},
        gauge={'axis': {'range': [0, 30]},
               'bar': {'color': "red"},
               'steps': [
                   {'range': [0, 10], 'color': "lightgreen"},
                   {'range': [10, 20], 'color': "yellow"},
                   {'range': [20, 30], 'color': "lightcoral"}]}
    ), row=2, col=1)

    # VaR
    fig.add_trace(go.Indicator(
        mode="number",
        value=risk['var_95'] * 100,
        title={'text': "VaR 95% (Daily)"},
        number={'suffix': "%"},
        domain={'x': [0, 1], 'y': [0, 1]}
    ), row=2, col=2)

    fig.update_layout(
        template='plotly_dark',
        height=600,
        showlegend=False
    )

    return fig

# ============================
# MAIN APPLICATION
# ============================

def main():
    """Main application entry point"""

    # Header
    st.markdown("""
    <div class="quant-header">
        <h1>🎯 Enhanced Wyckoff Analysis Pro</h1>
        <p>Professional Quantitative Trading System with Microstructure Integration</p>
        <p>Institutional-Grade Market Analysis Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Trading controls
        st.subheader("📅 Trading Controls")

        # Use configured data directory for parquet files
        data_dir = Path(st.secrets["data_directory"])

        # Symbol selection
        symbols = sorted([d.name for d in data_dir.iterdir() if d.is_dir()])
        symbol = st.selectbox("Symbol", symbols)

        # Timeframe selection with normalization and robust matching
        pair_dir = data_dir / symbol
        # Build raw file tuples (symbol, raw_tf, path)
        raw_file_tuples = [
            (p.stem.split('_')[0].upper(), p.stem.split('_')[1].lower(), p)
            for p in pair_dir.glob("*.parquet") if "_" in p.stem
        ]
        # Normalize timeframe codes to preferred format (m1, m3, ..., h1, d1, w1)
        file_tuples = []
        for sym, tf_raw, path in raw_file_tuples:
            if tf_raw.endswith('min'):
                tf_code = f"m{tf_raw.replace('min','')}"
            elif tf_raw.endswith('h'):
                tf_code = f"h{tf_raw.replace('h','')}"
            elif tf_raw.endswith('d'):
                tf_code = f"d{tf_raw.replace('d','')}"
            elif tf_raw.endswith('w'):
                tf_code = f"w{tf_raw.replace('w','')}"
            else:
                tf_code = tf_raw
            file_tuples.append((sym, tf_code, path))

        preferred_tfs = ['m1','m3','m5','m15','m30','h1','h4','d1','w1']
        # Filter available timeframes by preferred order
        available_tfs = {tf for _, tf, _ in file_tuples}
        tfs = [tf for tf in preferred_tfs if tf in available_tfs]
        if not tfs:
            st.error("No parquet files found for any preferred timeframe in this symbol directory.")
            df_analysis = None
        else:
            selected_tf = st.selectbox("Time-frame", tfs)
            # Find the corresponding file path(s)
            matching_paths = [path for _, tf, path in file_tuples if tf == selected_tf]
            if matching_paths:
                sel_path = matching_paths[0]
                df_analysis = pd.read_parquet(sel_path)
            else:
                st.error(f"No file found for selected timeframe: {selected_tf}")
                df_analysis = None

        # Analysis parameters
        st.subheader("📊 Analysis Parameters")

        lookback_period = st.slider(
            "Lookback Period (bars)",
            min_value=100,
            max_value=5000,
            value=140,  # default display bars
            step=50
        )

        # Advanced options
        with st.expander("🔧 Advanced Settings"):
            volume_threshold = st.slider("Volume Spike Threshold", 1.5, 4.0, 2.5, 0.1)
            manipulation_sensitivity = st.slider("Manipulation Sensitivity", 0.01, 0.1, 0.05, 0.01)
            phase_min_bars = st.slider("Min Bars for Phase", 10, 50, 20)

            enable_tick_analysis = st.checkbox("Enable Tick Analysis", value=False)
            enable_ml_features = st.checkbox("Enable ML Features", value=True)
            enable_alerts = st.checkbox("Enable Trading Alerts", value=True)

        # Analysis triggers
        st.subheader("🚀 Analysis")
        analyze_button = st.button("Run Analysis", type="primary", use_container_width=True)
        export_button = st.button("Export Results", use_container_width=True)

    # Main content area
    if analyze_button and df_analysis is not None and symbol is not None:
        # Progress indicator
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Initialize analyzer
        analyzer = EnhancedWyckoffAnalyzer()

        # Load tick data if available
        tick_data = None
        if enable_tick_analysis:
            # Load raw tick CSV from configured tick_data path
            tick_file = Path(st.secrets["tick_data"]) / f"{symbol}_tick.csv"
            if tick_file.exists():
                tick_data = pd.read_csv(tick_file, index_col=0, parse_dates=True)
                status_text.text("Loaded tick data for microstructure analysis...")

        # Prepare data
        status_text.text("Preparing data...")
        progress_bar.progress(10)

        # Trim data to lookback period
        df_analysis = df_analysis.tail(lookback_period).copy()

        # Run comprehensive analysis
        status_text.text("Running Wyckoff analysis...")
        progress_bar.progress(30)

        analysis_results = analyzer.comprehensive_analysis(df_analysis, tick_data)

        status_text.text("Analyzing microstructure patterns...")
        progress_bar.progress(60)

        # Display results
        status_text.text("Generating visualizations...")
        progress_bar.progress(80)

        # Clear progress indicators
        progress_bar.progress(100)
        status_text.empty()
        progress_bar.empty()

        # Display metrics dashboard
        st.subheader("📈 Key Metrics Dashboard")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            current_price = df_analysis['close'].iloc[-1]
            price_change = (df_analysis['close'].iloc[-1] - df_analysis['close'].iloc[0]) / df_analysis['close'].iloc[0] * 100
            st.metric("Price", f"${current_price:.2f}", f"{price_change:+.2f}%")

        with col2:
            if 'composite_operator' in analysis_results:
                phase = analysis_results['composite_operator']['phase']
                phase_color = {'Accumulation': '🟢', 'Distribution': '🔴', 'Neutral': '🟡'}
                st.metric("CO Phase", f"{phase_color.get(phase, '⚪')} {phase}")

        with col3:
            if 'manipulation_detection' in analysis_results:
                manip_score = analysis_results['manipulation_detection']['manipulation_score']
                st.metric("Manipulation", f"{manip_score:.1f}%",
                         "⚠️ High" if manip_score > 10 else "✅ Low")

        with col4:
            if 'risk_metrics' in analysis_results:
                risk_level = analysis_results['risk_metrics']['current_risk_level']
                risk_emoji = {'High Risk': '🔴', 'Medium Risk': '🟡', 'Low Risk': '🟢'}
                st.metric("Risk Level", f"{risk_emoji.get(risk_level, '⚪')} {risk_level}")

        with col5:
            if 'multi_timeframe' in analysis_results:
                alignment = analysis_results['multi_timeframe']['alignment']
                st.metric("MTF Alignment", alignment,
                         "✅" if alignment == 'Aligned' else "⚠️")

        # Wyckoff phases summary
        if 'wyckoff_phases' in analysis_results and analysis_results['wyckoff_phases']:
            st.subheader("🎯 Current Wyckoff Phase")
            latest_phase = analysis_results['wyckoff_phases'][-1]

            phase_col1, phase_col2 = st.columns([1, 3])
            with phase_col1:
                st.markdown(f"""
                <div class="phase-badge phase-{latest_phase['phase'].lower()}">
                    {latest_phase['phase']}
                </div>
                """, unsafe_allow_html=True)

            with phase_col2:
                st.write(f"**Confidence:** {latest_phase['confidence']:.0%}")
                st.write(f"**Price Range:** ${latest_phase['price_range'][0]:.2f} - ${latest_phase['price_range'][1]:.2f}")
                if 'characteristics' in latest_phase:
                    st.write(f"**Volume Trend:** {latest_phase['characteristics']['volume_trend']:.2f}x")

        # Main analysis chart
        st.subheader("📊 Enhanced Wyckoff Chart")
        # create_enhanced_wyckoff_chart is no longer used; replace/remove as appropriate.
        # If a chart is needed, use the UnifiedWyckoffEngine/analyzer object.
        # For now, we comment out/remove the function call:
        # main_chart = create_enhanced_wyckoff_chart(df_analysis, analysis_results, symbol)
        # st.plotly_chart(main_chart, use_container_width=True, config={"displayModeBar": False})

        # User prompt for advanced analysis
        st.subheader("🤖 Ask about the Analysis")
        user_query = st.text_area(
            "Enter a question about the advanced analysis results below:",
            ""
        )
        if user_query:
            if st.button("Get Advanced Insight", key="analysis_prompt_btn"):
                with st.spinner("Generating insight..."):
                    # Build the prompt with context
                    context = json.dumps(analysis_results, indent=2, default=str)
                    messages = [
                        {"role": "system", "content": "You are a professional financial analysis assistant."},
                        {"role": "user", "content": f"Here are the analysis results:\n{context}\n\nQuestion: {user_query}\nPlease provide a detailed answer based on the analysis above."}
                    ]
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=messages,
                        temperature=0.2,
                    )
                    reply = response.choices[0].message.content
                    st.markdown("**Insight:**")
                    st.write(reply)

        # Additional visualizations in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Volume Profile",
            "🏛️ Institutional Activity",
            "🚨 Manipulation Detection",
            "⚠️ Risk Dashboard",
            "💼 Trade Setups"
        ])

        with tab1:
            volume_profile_chart = create_volume_profile_chart(df_analysis, analysis_results)
            st.plotly_chart(volume_profile_chart, use_container_width=True)

            # Volume analysis insights
            if 'volume_profile' in analysis_results:
                st.info(f"**POC (Point of Control):** ${analysis_results['volume_profile']['poc']:.2f}")

        with tab2:
            col1, col2 = st.columns(2)

            with col1:
                institutional_chart = create_institutional_activity_chart(analysis_results)
                st.plotly_chart(institutional_chart, use_container_width=True)

            with col2:
                if 'composite_operator' in analysis_results:
                    co = analysis_results['composite_operator']
                    st.write("### Institutional Footprints")
                    st.write(f"**Accumulation Score:** {co['accumulation_score']:.1f}%")
                    st.write(f"**Distribution Score:** {co['distribution_score']:.1f}%")

                    if co['institutional_footprints']:
                        recent_footprints = co['institutional_footprints'][-5:]
                        for fp in recent_footprints:
                            st.write(f"- {fp['type']} (Strength: {fp['strength']:.1f}x)")

        with tab3:
            if 'manipulation_detection' in analysis_results:
                manipulation_heatmap = create_manipulation_heatmap(analysis_results, df_analysis)
                st.plotly_chart(manipulation_heatmap, use_container_width=True)

                # Manipulation events summary
                manip = analysis_results['manipulation_detection']

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Stop Hunts", len(manip.get('stop_hunts', [])))
                with col2:
                    st.metric("Spoofing Events", len(manip.get('spoofing_events', [])))
                with col3:
                    st.metric("Wash Trades", len(manip.get('wash_trades', [])))

                # Recent manipulation alerts
                if manip.get('stop_hunts'):
                    st.markdown("""
                    <div class="manipulation-alert">
                        ⚠️ Recent stop hunt activity detected! Exercise caution with stops.
                    </div>
                    """, unsafe_allow_html=True)

        with tab4:
            risk_dashboard = create_risk_dashboard(analysis_results)
            st.plotly_chart(risk_dashboard, use_container_width=True)

            # Risk recommendations
            if 'risk_metrics' in analysis_results:
                risk = analysis_results['risk_metrics']
                if risk['current_risk_level'] == 'High Risk':
                    st.warning("⚠️ High risk environment detected. Consider reducing position sizes.")
                elif risk['current_risk_level'] == 'Low Risk':
                    st.success("✅ Low risk environment. Favorable conditions for position entry.")

        with tab5:
            st.write("### 💼 Professional Trade Setups")

            if 'trade_setups' in analysis_results and analysis_results['trade_setups']:
                for setup in analysis_results['trade_setups']:
                    with st.expander(f"{setup['name']} - Confidence: {setup['confidence']:.0%}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Entry:** ${setup['entry']:.2f}")
                            st.write(f"**Stop:** ${setup['stop']:.2f}")
                            st.write(f"**Risk/Reward:** {setup['risk_reward']:.1f}")

                        with col2:
                            st.write("**Targets:**")
                            for i, target in enumerate(setup['targets'], 1):
                                st.write(f"  T{i}: ${target:.2f}")

                        st.write(f"**Notes:** {setup.get('notes', 'N/A')}")

                        # Add trade button
                        if st.button(f"Execute {setup['name']}", key=f"trade_{setup['name']}"):
                            st.success(f"Trade setup copied to clipboard!")
            else:
                st.info("No high-confidence trade setups currently available.")

        # Export functionality
        if export_button:
            # Create comprehensive export
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'analysis': analysis_results,
                'parameters': {
                    'lookback_period': lookback_period,
                    'volume_threshold': volume_threshold,
                    'manipulation_sensitivity': manipulation_sensitivity
                }
            }

            # Convert to JSON
            export_json = json.dumps(export_data, indent=2, default=str)

            # Download button
            st.download_button(
                label="📥 Download Analysis Report",
                data=export_json,
                file_name=f"wyckoff_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888;">
        <p><strong>Enhanced Wyckoff Analysis Pro v4.0</strong></p>
        <p>Professional Quantitative Trading System</p>
        <p>Powered by Advanced Microstructure Analysis</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
