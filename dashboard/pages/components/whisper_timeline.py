import time
import requests
import streamlit as st
from dashboard.utils.streamlit_api import api_url


def render_whisper_timeline(limit: int = 100):
    try:
        data = requests.get(api_url("api/pulse/whispers/log"), timeout=2).json()
        items = list(reversed(data.get('log', [])))[:limit]
    except Exception:
        st.info("Whisper timeline unavailable.")
        return
    st.caption("Whisperer Audit Trail")
    for it in items:
        ts = it.get('ts') or time.time()
        tstr = time.strftime('%H:%M:%S', time.localtime(float(ts)))
        st.write(f"{tstr} – {it.get('text','')} ")
