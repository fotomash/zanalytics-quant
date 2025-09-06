import streamlit as st
from dashboard_integration import ZanflowDataConnector, integrate_home_dashboard

# Initialize connector
@st.cache_resource
def get_connector():
    return ZanflowDataConnector()

connector = get_connector()

# Your existing home.py code here...
# Add this to integrate with API:
integrate_home_dashboard(connector)

# Or use individual functions:
# symbols = connector.get_all_symbols()
# data = connector.get_symbol_data("EURUSD")
# history = connector.get_symbol_history("EURUSD")
