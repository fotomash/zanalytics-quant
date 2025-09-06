import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Pulse Behavioral Trading", layout="wide")

# API configuration
DJANGO_API_URL = st.secrets.get("DJANGO_API_URL", "http://localhost:8000")

def fetch_pulse_health():
    """Fetch Pulse system health"""
    response = requests.get(f"{DJANGO_API_URL}/api/pulse/health/")
    return response.json() if response.ok else None

def fetch_risk_status():
    """Fetch current risk status"""
    response = requests.get(f"{DJANGO_API_URL}/api/pulse/risk/")
    return response.json() if response.ok else None

def fetch_active_signals():
    """Fetch active trading signals"""
    response = requests.get(f"{DJANGO_API_URL}/api/pulse/signals/")
    return response.json() if response.ok else None

# Main dashboard
st.title("🎯 Zanalytics Pulse - Behavioral Trading System")

# Create layout
col1, col2, col3 = st.columns([1, 2, 1])

# Health Status Panel
with col1:
    st.subheader("📊 System Health")
    health = fetch_pulse_health()
    if health:
        st.metric("Status", health['status'].upper())
        st.metric("Active Signals", health['active_signals'])

        # Behavioral health indicators
        bh = health['behavioral_health']
        if bh.get('overtrading_risk'):
            st.warning("⚠️ Overtrading Risk Detected")
        if bh.get('cooling_off_active'):
            st.info("❄️ Cooling-off Period Active")
        if not bh.get('daily_loss_safe'):
            st.error("🚨 Daily Loss Limit Approaching")

# Risk Status Panel
with col3:
    st.subheader("🛡️ Risk Protection")
    risk = fetch_risk_status()
    if risk:
        state = risk['current_state']

        # Display key metrics
        st.metric("Confidence Level", f"{state['confidence_level']:.0%}")
        st.metric("Daily P&L", f"{state['daily_pnl_percent']:.2%}")
        st.metric("Trades Today", state['trades_today'])

        # Emotional state indicator
        emotional_state = state['emotional_state']
        if emotional_state == 'neutral':
            st.success(f"😊 Emotional State: {emotional_state}")
        elif emotional_state == 'confident':
            st.info(f"💪 Emotional State: {emotional_state}")
        else:
            st.warning(f"😰 Emotional State: {emotional_state}")

        # Recommendations
        if risk.get('recommendations'):
            st.subheader("💡 Recommendations")
            for rec in risk['recommendations']:
                st.write(f"• {rec}")

# Main Signal Display
with col2:
    st.subheader("📈 Active Trading Signals")

    signals = fetch_active_signals()
    if signals:
        for symbol, signal in signals.items():
            with st.expander(f"{symbol} - Score: {signal['confluence_score']:.1f}%"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Entry:** {signal['entry_price']}")
                    st.write(f"**Stop Loss:** {signal['stop_loss']}")
                    st.write(f"**Take Profit:** {signal['take_profit']}")
                with col_b:
                    st.write(f"**Position Size:** {signal['position_size']:.2%}")
                    st.write(f"**Time:** {signal['timestamp']}")
                st.write(f"**Reasoning:** {signal['reasoning']}")
    else:
        st.info("No active signals at the moment")

# Auto-refresh
if st.button("🔄 Refresh"):
    st.rerun()

# Auto-refresh every 5 seconds
st.markdown(
    """
    <script>
    setTimeout(function(){
        window.location.reload();
    }, 5000);
    </script>
    """,
    unsafe_allow_html=True
)
