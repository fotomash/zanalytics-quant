
import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="ZANFLOW v12 Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("🌊 ZANFLOW v12 - Trading Intelligence Platform")

# Check API status
try:
    response = requests.get('http://localhost:5000/api/status')
    if response.status_code == 200:
        status = response.json()
        st.success(f"✅ API Status: {status['status']}")
    else:
        st.error("❌ API is not responding")
except:
    st.warning("⚠️ API connection failed - make sure the API server is running")

# Main dashboard content
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Active Strategies", "3", "+1")

with col2:
    st.metric("Total Signals", "127", "+12")

with col3:
    st.metric("Win Rate", "67.3%", "+2.1%")

st.markdown("---")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📈 Market Analysis", "🎯 Strategies", "📊 Performance", "⚙️ Settings"])

with tab1:
    st.header("Market Analysis")
    st.info("Market analysis components will be loaded here")

with tab2:
    st.header("Active Strategies")
    strategies = pd.DataFrame({
        'Strategy': ['London Kill Zone', 'MIDAS Curve', 'Wyckoff Analysis'],
        'Status': ['Active', 'Active', 'Monitoring'],
        'Performance': ['+12.3%', '+8.7%', '+5.2%']
    })
    st.dataframe(strategies)

with tab3:
    st.header("Performance Metrics")
    st.info("Performance charts will be displayed here")

with tab4:
    st.header("System Settings")
    st.info("Configuration options will be available here")
