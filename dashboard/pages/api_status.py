import streamlit as st
import requests
import os

st.set_page_config(page_title="API Monitor", layout="wide")

st.title("📡 API Status Dashboard")

API_ENDPOINTS = {
    "Fred": f"https://api.stlouisfed.org/fred/series?series_id=GDP&api_key={os.getenv('FRED_API_KEY')}&file_type=json",
    "Example": "https://api.example.com/status"  # Add more endpoints here
}

for name, url in API_ENDPOINTS.items():
    st.subheader(f"{name} API")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        st.success(f"{name} is up ✅")
        if "application/json" in r.headers.get("Content-Type", ""):
            st.json(r.json())
        else:
            st.text(r.text)
    except Exception as e:
        st.error(f"{name} is down ❌")
        st.code(str(e))