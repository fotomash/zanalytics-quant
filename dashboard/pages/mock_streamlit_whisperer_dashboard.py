import streamlit as st
from utils import bipolar_donut, oneway_donut  # Assume pre-defined donut renderers

st.set_page_config(page_title="Whisperer Dashboard", layout="wide")

st.title("🧠 Whisperer Dashboard - Trading Session Overview")

# Symbol Selector
symbols = ["XAUUSD", "EURUSD", "SPX500"]  # example list
sel_symbol = st.selectbox("Select Symbol", symbols)

# SESSION METRICS
st.header("📊 Session Metrics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Start of Day Balance", "$50,000")
    st.metric("Current Equity", "$51,250")
with col2:
    st.metric("Risk Used", "1.5%")
    st.metric("Stop Target", "3.0% (max loss)")
with col3:
    st.metric("Win Target", "2.5% (goal)")
    st.metric("Time to News", "00:12:34")

# DONUTS ROW
st.subheader("🧁 Equity & Behavioral Posture")
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(bipolar_donut(
        title="Equity vs Risk",
        value=1250,  # pnl
        pos_max=1250,
        neg_max=-1500,
        start_anchor="top",
        center_title="$51.2k",
        center_sub="+$1.25k today"
    ), use_container_width=True)

with c2:
    st.plotly_chart(oneway_donut(
        title="Behavioral Posture",
        frac=0.76,
        start_anchor="top",
        center_title="76",
        center_sub="Composite Score"
    ), use_container_width=True)

# TRADE METRICS
st.header("📈 Trade Metrics")
st.write("⏱ Time in Trade: 00:23:19")
st.write("📊 Entry Confidence: High")
st.write("📉 Unrealized PnL: -$75")
st.write("⚠️ Max Adverse Excursion: $130")

# BEHAVIORAL METRICS
st.header("🧠 Behavioral Feedback")
colb1, colb2, colb3 = st.columns(3)
with colb1:
    st.metric("Patience Index", "94s avg wait")
    st.metric("Break Adherence", "Yes")
with colb2:
    st.metric("Conviction Accuracy", "67%")
with colb3:
    st.metric("Profit Efficiency", "58%")

st.caption("Note: News timing, alerts, and PnL-based triggers are pre-configured via YAML.")