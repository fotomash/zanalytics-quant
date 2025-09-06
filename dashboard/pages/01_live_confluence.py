import time

import requests
import streamlit as st

API_BASE = "http://localhost:8080"


def fetch_real_score(symbol: str) -> dict:
    """Retrieve a real-time confluence score from the API."""
    try:
        resp = requests.get(f"{API_BASE}/score/peek", params={"symbol": symbol}, timeout=5)
        return resp.json()
    except Exception:
        return {"error": "API unavailable"}


def fetch_risk_state() -> dict:
    """Retrieve the current risk state from the API."""
    try:
        resp = requests.get(f"{API_BASE}/risk/summary", timeout=5)
        return resp.json()
    except Exception:
        return {"trades_left": 0, "daily_loss_pct": 0, "fatigue_level": 0, "cooling_off": False}


st.title("🎯 Live Confluence Monitor")

col1, col2, col3 = st.columns(3)
symbols = ["EURUSD", "GBPUSD", "USDJPY"]
placeholders = [col1.empty(), col2.empty(), col3.empty()]

while True:
    for i, symbol in enumerate(symbols):
        score_data = fetch_real_score(symbol)
        if "error" not in score_data:
            placeholders[i].metric(
                label=symbol,
                value=f"{score_data['score']}",
                delta=f"Grade: {score_data['grade']}"
            )
    risk = fetch_risk_state()
    st.sidebar.metric("Trades Left", risk.get("trades_left", 0))
    st.sidebar.metric("Daily Loss", f"{risk.get('daily_loss_pct', 0):.2%}")
    time.sleep(1)
