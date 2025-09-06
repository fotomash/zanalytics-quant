import os, pandas as pd, plotly.graph_objects as go, streamlit as st
from app.wiring.pulse_runtime import runtime

st.set_page_config(page_title="Zanalytics Pulse", layout="wide")

# ---------- HEADER ----------
st.markdown("# 🧠 Zanalytics Pulse – Trading Intelligence")
st.caption("Discipline through data • Real-time risk management • Explainable confluence")

# ---------- DECISION SURFACE ----------
with st.container():
    st.subheader("🎯 Decision Surface (live confluence + risk)")

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        symbol = st.text_input("Symbol", value="EURUSD")
    with c2:
        price = st.number_input("Snapshot price", value=1.0850, format="%.5f")
    with c3:
        if st.button("Score Now"):
            st.session_state["_score_now"] = True

    decision = None
    if st.session_state.get("_score_now"):
        decision = runtime.score_symbol_snapshot(symbol, float(price))
        st.session_state["_score_now"] = False

    # Tiles
    t1, t2, t3 = st.columns(3)
    if decision:
        conf = int(decision.get("confidence", 0))
        reasons = decision.get("reasons", [])
        risk_warnings = decision.get("warnings", [])
        action = decision.get("action", "none")

        with t1:
            st.metric("Confluence Score", f"{conf}/100")
            if st.toggle("Explain score"):
                for r in reasons[:6]:
                    st.caption(f"• {r}")

        with t2:
            st.metric("Kernel Decision", action.upper())
            if risk_warnings:
                st.warning(" / ".join(risk_warnings))
            else:
                st.success("No active risk warnings")

        with t3:
            status = runtime.kernel.get_status() if hasattr(runtime.kernel, "get_status") else {}
            st.metric("Trades today", f"{status.get('daily_stats',{}).get('trades_count',0)}/5")
            st.metric("Daily P&L", f"${status.get('daily_stats',{}).get('pnl',0):,.2f}")

st.divider()

# ---------- REAL PERFORMANCE ----------
st.subheader("📊 Real Performance (from MT5 history)")
df = runtime.trade_history_df(days_back=30)
if df is None:
    st.warning("⚠️ MT5 not connected. Set MT5_ACCOUNT/MT5_PASSWORD/MT5_SERVER and reload.")
elif df.empty:
    st.info("No MT5 trade history found in the selected period.")
else:
    # top metrics
    win_rate = (df['profit'] > 0).mean() * 100
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Win Rate", f"{win_rate:.1f}%")
    with c2: st.metric("Total P&L", f"${df['profit'].sum():,.2f}")
    with c3: st.metric("Trades", f"{len(df)}")
    with c4: st.metric("Avg Risk Score", f"{df['behavioral_risk_score'].mean():.1f}/10")

    st.dataframe(
        df[["time","symbol","volume","profit","is_win","revenge_trade","overconfidence","fatigue_trade","fomo_trade","behavioral_risk_score"]]
        .sort_values("time", ascending=False)
        .head(300),
        use_container_width=True
    )

st.divider()

# ---------- CONFLUENCE VALIDATION ----------
st.subheader("🔬 Confluence Validation (real scores vs outcomes)")
val = runtime.confluence_validation_df()
if val is None:
    st.info("Connect MT5 to validate.")
elif val.empty:
    st.warning("No trades with saved confluence scores yet (journal empty or unmatched).")
else:
    fig = go.Figure()
    fig.add_bar(x=val.index.astype(str), y=val["win_rate"], name="Win Rate %")
    fig.add_scatter(x=val.index.astype(str), y=val["avg_pnl"], name="Avg P&L", yaxis="y2")
    fig.update_layout(
        xaxis_title="Confluence Band",
        yaxis=dict(title="Win Rate %"),
        yaxis2=dict(title="Avg P&L ($)", overlaying="y", side="right"),
        height=420, hovermode="x unified", title="Validation of scoring → outcomes"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- WEEKLY REVIEW / COACHING ----------
st.subheader("🧠 Weekly Review & Coaching")
review = runtime.weekly_review()
if "error" in review:
    st.info(review["error"])
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total P&L (Week)", f"${review['summary']['total_pnl']:,.2f}")
        st.metric("Win Rate", f"{review['summary']['win_rate']:.1f}%")
    with c2:
        st.metric("Trades", review['summary']['total_trades'])
        st.metric("Best Day", review['summary']['best_day'])
    with c3:
        st.metric("Worst Day", review['summary']['worst_day'])
        st.metric("Avg Behavioral Risk", f"{review['summary']['avg_risk_score']:.1f}")

    if review.get("recommendations"):
        st.warning("Recommendations")
        for r in review["recommendations"]:
            st.write(f"• {r}")

st.divider()

# ---------- JOURNAL SYNC ----------
st.subheader("📝 Journal")
colA, colB = st.columns([1,3])
with colA:
    if st.button("Sync MT5 → Journal"):
        n = runtime.sync_journal()
        st.success(f"Synced {n} entries to journal.")
with colB:
    jp = os.getenv("PULSE_JOURNAL_PATH", "signal_journal.json")
    st.caption(f"Journal path: `{jp}`")
    if os.path.exists(jp):
        st.code(open(jp).read()[:3000], language="json")
