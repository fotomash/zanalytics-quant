import os
import time
import requests
import streamlit as st


def render_whisper_timeline(limit: int = 100):
    dj = os.getenv("DJANGO_API_URL", "http://django:8000").rstrip('/')
    try:
        data = requests.get(f"{dj}/api/pulse/whispers/log", timeout=2).json()
        items = list(reversed(data.get('log', [])))[:limit]
    except Exception:
        st.info("Whisper timeline unavailable.")
        return
    st.caption("Whisperer Audit Trail")
    for it in items:
        ts = it.get('ts') or time.time()
        tstr = time.strftime('%H:%M:%S', time.localtime(float(ts)))
        st.write(f"{tstr} – {it.get('text','')} ")

