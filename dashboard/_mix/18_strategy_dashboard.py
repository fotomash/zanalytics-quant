import os
import requests
import streamlit as st
from dashboard.utils.streamlit_api import render_analytics_filters

API_BASE = os.getenv("DJANGO_API_URL", "http://django:8000")

st.title("Strategy Dashboard")
_sym18, _df18, _dt18, _qs18 = render_analytics_filters(key_prefix='p18')

symbol = st.text_input("Symbol", "XAUUSD")

if st.button("Match Strategy"):
    try:
        resp = requests.get(f"{API_BASE}/api/strategy/match", params={"symbol": symbol}, timeout=5)
        data = resp.json()
        st.json(data)
    except Exception as exc:
        st.error(f"API error: {exc}")
