import streamlit as st
import json
import os
import requests
import pandas as pd

st.set_page_config(page_title="PULSE Predictive Flow", page_icon="🧠", layout="wide")
st.title("PULSE Predictive Flow Framework")

# Load playbook JSON
def load_playbook():
    try:
        with open("config/playbooks/pulse_v1.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Unable to load playbook: {e}")
        return {"gates": []}

playbook = load_playbook()

# Symbol selector
symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "SPX500"]
symbol = st.selectbox("Symbol", symbols, index=0)

# Gate table (human narrative)
if playbook.get("gates"):
    gate_df = pd.DataFrame([
        {"Gate": g.get("name"), "Rule": g.get("rule"), "Optional": g.get("optional", False)}
        for g in playbook["gates"]
    ])
    st.dataframe(gate_df, use_container_width=True)
else:
    st.info("No gates found in playbook.")

st.divider()
st.subheader("Live Status")

def fetch_status(sym: str):
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    try:
        r = requests.get(f"{base}/api/v1/feed/pulse-status", params={"symbol": sym}, timeout=1.5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

status = fetch_status(symbol)
cols = st.columns(max(1, len(playbook.get("gates", []))))
for col, gate in zip(cols, playbook.get("gates", [])):
    state = status.get(gate.get("id"), 0)
    color = "#00cc96" if state else "#ef553b"
    label = gate.get("name") or gate.get("id")
    col.markdown(
        f"<div style='text-align:center; font-weight:600; color:{color}'>"
        f"{label}<br>●</div>",
        unsafe_allow_html=True
    )
