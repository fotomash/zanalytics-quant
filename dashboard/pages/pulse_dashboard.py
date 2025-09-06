import streamlit as st
from utils.pulse_api import (
    get_score_peek,
    get_risk_summary,
    get_top_signals,
    get_recent_journal,
)

st.set_page_config(page_title="Pulse Behavioral Trading", layout="wide")
st.title("🎯 Zanalytics Pulse - Behavioral Trading System")

score = get_score_peek()
risk = get_risk_summary()
sigs = get_top_signals(3)
jrnl = get_recent_journal(5)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Confluence")
    st.metric("Score", score.get("score", 0))
    for r in score.get("reasons", []):
        st.write(f"- {r}")

with col2:
    st.subheader("🛡️ Risk")
    st.write(risk)

st.subheader("🚀 Opportunities")
for s in sigs:
    st.write(f"{s.get('symbol')} ({s.get('bias')}) - {s.get('score')}")
    st.write(", ".join(s.get("reasons", [])))

st.subheader("📝 Journal")
for j in jrnl:
    ts = j.get("timestamp")
    sym = j.get("symbol")
    pnl = j.get("pnl")
    note = j.get("note")
    st.write(f"{ts} {sym} {pnl} {note}")
