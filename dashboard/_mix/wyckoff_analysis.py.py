# dashboard/pages/wyckoff_analysis.py
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import asyncio
from dashboard.config import get_api_url

# Configuration
API_BASE_URL = st.secrets.get("API_BASE_URL", get_api_url())

def render_page():
    """Render the unified Wyckoff analysis page"""
    
    st.header("🏛️ Unified Wyckoff Analysis")
    st.markdown("*Professional Wyckoff Method Analysis with VSA Integration*")
    
    # Data selection (your existing logic)
    with st.sidebar:
        st.subheader("📊 Data Selection")
        
        # Symbol selection
        symbol = st.selectbox("Select Symbol", ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"])
        
        # Load data (your existing parquet loading logic)
        df = load_market_data(symbol)  # Your existing function
        
        if df is not None and not df.empty:
            st.success(f"✅ Loaded {len(df)} bars")
            
            # Analysis configuration
            st.subheader("⚙️ Analysis Config")
            
            config = {
                'volume_threshold': st.slider("Volume Threshold", 1.0, 3.0, 1.5, 0.1),
                'phase_sensitivity': st.slider("Phase Sensitivity", 0.5, 2.0, 1.0, 0.1),
                'lookback_periods': st.slider("Lookback Periods", 50, 200, 100, 10)
            }
            
            # Run analysis button
            if st.button("🚀 Run Unified Analysis", type="primary"):
                run_wyckoff_analysis(symbol, df, config)
        else:
            st.error("❌ No data available")

def run_wyckoff_analysis(symbol: str, df: pd.DataFrame, config: dict):
    """Run Wyckoff analysis via API"""
    
    with st.spinner("Running comprehensive Wyckoff analysis..."):
        try:
            # Prepare data for API
            data_records = df.to_dict('records')
            
            # Make API request
            response = requests.post(
                f"{API_BASE_URL}/wyckoff/analyze",
                json={
                    'symbol': symbol,
                    'data': data_records,
                    'config': config
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                display_analysis_results(symbol, result['analysis'], result.get('cache_hit', False))
            else:
                st.error(f"Analysis failed: {response.text}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

def display_analysis_results(symbol: str, analysis: dict, cache_hit: bool):
    """Display comprehensive analysis results"""
    
    # Cache status
    if cache_hit:
        st.info("📋 Results loaded from cache")
    else:
        st.success("✨ Fresh analysis completed")
    
    # Key metrics
    st.subheader("📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        phase = analysis['current_phase'].title()
        confidence = analysis['phase_confidence']
        st.metric("Current Phase", phase, f"{confidence:.1%} confidence")
    
    with col2:
        duration = analysis['phase_duration']
        st.metric("Phase Duration", f"{duration} bars")
    
    with col3:
        co_score = analysis['composite_operator_score']
        co_status = "Accumulating" if co_score > 0.2 else "Distributing" if co_score < -0.2 else "Neutral"
        st.metric("Composite Operator", co_status, f"{co_score:.2f}")
    
    with col4:
        trend = analysis['trend_structure']['trend'].title()
        st.metric("Market Trend", trend)
    
    # Phase visualization
    st.subheader("📈 Phase Analysis")
    
    # Create phase timeline chart
    create_phase_timeline_chart(analysis)
    
    # Events analysis
    if analysis['events']:
        st.subheader("🎯 Wyckoff Events")
        
        events_df = pd.DataFrame([
            {
                'Event': event['event_type'],
                'Time': event['timestamp'],
                'Price': f"${event['price']:.2f}",
                'Volume': f"{event['volume']:,.0f}",
                'Significance': event['significance'],
                'Confidence': f"{event['confidence']:.1%}",
                'Description': event['description']
            }
            for event in analysis['events']
        ])
        
        st.dataframe(events_df, use_container_width=True)
    
    # Trade setups
    if analysis['trade_setups']:
        st.subheader("💼 Trade Setups")
        
        for setup in analysis['trade_setups']:
            render_trade_setup_card(setup)
    
    # VSA Analysis
    if analysis['vsa_signals']:
        st.subheader("📊 Volume Spread Analysis")
        
        with st.expander("VSA Signals Details"):
            st.json(analysis['vsa_signals'])
    
    # Supply/Demand Zones
    zones = analysis['supply_demand_zones']
    if zones['supply_zones'] or zones['demand_zones']:
        st.subheader("🎯 Supply & Demand Zones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Supply Zones**")
            if zones['supply_zones']:
                supply_df = pd.DataFrame(zones['supply_zones'])
                st.dataframe(supply_df, use_container_width=True)
            else:
                st.info("No significant supply zones")
        
        with col2:
            st.write("**Demand Zones**")
            if zones['demand_zones']:
                demand_df = pd.DataFrame(zones['demand_zones'])
                st.dataframe(demand_df, use_container_width=True)
            else:
                st.info("No significant demand zones")
        
        st.write(f"**Current Bias:** {zones['current_bias'].replace('_', ' ').title()}")

def render_trade_setup_card(setup: dict):
    """Render individual trade setup card"""
    
    # Determine card color based on confidence
    confidence = setup.get('confidence', 0.5)
    if confidence >= 0.8:
        color = "#4CAF50"  # Green
    elif confidence >= 0.6:
        color = "#FF9800"  # Orange
    else:
        color = "#2196F3"  # Blue
    
    targets_str = ", ".join([f"${t:.2f}" for t in setup.get('targets', [])])
    
    st.markdown(f"""
    <div style='border-left: 6px solid {color}; padding: 1rem; margin: 0.5rem 0; 
                background: rgba(255,255,255,0.05); border-radius: 8px;'>
        <h4 style='margin: 0; color: {color};'>{setup['name']}</h4>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); 
                    gap: 10px; margin-top: 10px;'>
            <div><strong>Type:</strong> {setup['type'].upper()}</div>
            <div><strong>Entry:</strong> ${setup['entry']:.2f}</div>
            <div><strong>Stop:</strong> ${setup['stop']:.2f}</div>
            <div><strong>R/R:</strong> {setup['risk_reward']:.1f}</div>
        </div>
        <div style='margin-top: 10px;'>
            <strong>Targets:</strong> {targets_str}
        </div>
        <div style='margin-top: 10px; font-size: 0.9em; opacity: 0.8;'>
            <strong>Phase:</strong> {setup['phase'].title()} | 
            <strong>Confidence:</strong> {confidence:.1%}
        </div>
        <div style='margin-top: 5px; font-size: 0.85em; font-style: italic;'>
            {setup['description']}
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_phase_timeline_chart(analysis: dict):
    """Create phase timeline visualization"""
    
    # This would create a timeline showing phase transitions
    # Implementation depends on your specific visualization needs
    
    fig = go.Figure()
    
    # Add phase indicator
    current_phase = analysis['current_phase']
    confidence = analysis['phase_confidence']
    
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=confidence * 100,
        title={'text': f"Phase: {current_phase.title()}"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': get_phase_color(current_phase)},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "gray"},
                {'range': [80, 100], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

def get_phase_color(phase: str) -> str:
    """Get color for Wyckoff phase"""
    colors = {
        'accumulation': '#4CAF50',
        'markup': '#2196F3', 
        'distribution': '#FF9800',
        'markdown': '#f44336',
        'transition': '#9E9E9E'
    }
    return colors.get(phase.lower(), '#9E9E9E')

def load_market_data(symbol: str) -> pd.DataFrame:
    """Load market data - your existing implementation"""
    # Your existing data loading logic here
    pass