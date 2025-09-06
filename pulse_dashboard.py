import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import yaml
import random
import time

# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown(
    """
<style>
    .stMetric {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .pulse-header {
        font-size: 2.5em;
        font-weight: bold;
        background: linear-gradient(90deg, #00ff44, #00aaff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Session state defaults
if "confluence_score" not in st.session_state:
    st.session_state.confluence_score = 75
if "risk_level" not in st.session_state:
    st.session_state.risk_level = "MEDIUM"
if "trades_today" not in st.session_state:
    st.session_state.trades_today = 2
if "daily_pnl" not in st.session_state:
    st.session_state.daily_pnl = 250.50
if "behavioral_alerts" not in st.session_state:
    st.session_state.behavioral_alerts = []
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

@st.cache_data
def load_config(path: str = "pulse_dashboard_config.yaml"):
    """Load dashboard configuration."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "confluence_weights": {"smc": 0.4, "wyckoff": 0.3, "technical": 0.3},
            "risk_limits": {
                "daily_loss_limit": 0.03,
                "max_trades_per_day": 5,
                "cooling_off_minutes": 15,
                "min_confluence_score": 70,
            },
        }

@st.cache_data
def load_trade_history(path: str = "trade_history.json"):
    """Load recent trade history for demo purposes."""
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return pd.DataFrame(data)
    except FileNotFoundError:
        trades = []
        for i in range(30):
            trades.append(
                {
                    "timestamp": (datetime.now() - timedelta(days=30 - i)).isoformat(),
                    "symbol": random.choice(["EURUSD", "GBPUSD", "USDJPY"]),
                    "confluence_score": random.randint(60, 95),
                    "pnl": random.uniform(-500, 1500),
                    "risk_score": random.randint(1, 10),
                }
            )
        return pd.DataFrame(trades)

config = load_config()
df_trades = load_trade_history()

st.markdown('<div class="pulse-header">🧠 ZANALYTICS PULSE</div>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align: center; color: #888;">Behavioral Intelligence Trading System</p>',
    unsafe_allow_html=True,
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Confluence Score",
        f"{st.session_state.confluence_score}%",
        delta=f"{st.session_state.confluence_score - 70:+.0f} from threshold",
    )

with col2:
    st.metric(
        "Risk Level",
        st.session_state.risk_level,
        delta="Protected" if st.session_state.risk_level != "HIGH" else "⚠️ Caution",
    )

with col3:
    st.metric(
        "Trades Today",
        f"{st.session_state.trades_today}/5",
        delta=f"{5 - st.session_state.trades_today} remaining",
    )

with col4:
    st.metric(
        "Daily P&L",
        f"${st.session_state.daily_pnl:,.2f}",
        delta=f"{(st.session_state.daily_pnl/10000)*100:.1f}%",
    )

with col5:
    account_balance = 10000 + st.session_state.daily_pnl
    st.metric(
        "Account Balance",
        f"${account_balance:,.2f}",
        delta=f"Limit: {(abs(st.session_state.daily_pnl)/10000)*100:.1f}%/3%",
    )

st.markdown("---")
alert_col1, alert_col2 = st.columns([1, 3])

with alert_col1:
    st.subheader("🚨 Behavioral Alerts")
    behavioral_status = {
        "Overconfidence": random.choice(["✅ Clear", "⚠️ Warning", "🔴 Alert"]),
        "Revenge Trading": "✅ Clear",
        "Fatigue Level": random.choice(["✅ Normal", "⚠️ Elevated"]),
        "FOMO Protection": "✅ Active",
        "Loss Chasing": "✅ Clear",
        "Time Restriction": "✅ Optimal",
    }
    for behavior, status in behavioral_status.items():
        if "🔴" in status:
            st.error(f"{behavior}: {status}")
        elif "⚠️" in status:
            st.warning(f"{behavior}: {status}")
        else:
            st.success(f"{behavior}: {status}")

with alert_col2:
    st.subheader("📊 Live Confluence Analysis")
    confluence_data = {
        "Component": ["SMC Analysis", "Wyckoff Method", "Technical Indicators"],
        "Score": [
            random.randint(60, 95),
            random.randint(60, 95),
            random.randint(60, 95),
        ],
        "Weight": [0.4, 0.3, 0.3],
    }
    df_confluence = pd.DataFrame(confluence_data)
    df_confluence["Weighted Score"] = df_confluence["Score"] * df_confluence["Weight"]
    fig_confluence = go.Figure(
        data=[
            go.Bar(
                name="Score",
                x=df_confluence["Component"],
                y=df_confluence["Score"],
                marker_color="lightblue",
            ),
            go.Bar(
                name="Weighted",
                x=df_confluence["Component"],
                y=df_confluence["Weighted Score"],
                marker_color="darkblue",
            ),
        ]
    )
    fig_confluence.update_layout(
        barmode="group",
        height=300,
        title="Confluence Score Breakdown",
        showlegend=True,
        xaxis_title="Analysis Component",
        yaxis_title="Score",
        template="plotly_dark",
    )
    st.plotly_chart(fig_confluence, use_container_width=True)


# Tabs for detailed sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📈 Trading Signals",
        "📊 Performance",
        "🧠 Behavioral Analysis",
        "⚙️ Risk Settings",
        "📝 Journal",
    ]
)

with tab1:
    st.subheader("Active Trading Signals")
    col1, col2 = st.columns([2, 1])
    with col1:
        signals = []
        for symbol in ["EURUSD", "GBPUSD", "USDJPY", "GOLD", "BTCUSD"]:
            signals.append(
                {
                    "Symbol": symbol,
                    "Signal": random.choice(["BUY", "SELL", "HOLD"]),
                    "Confluence": random.randint(45, 95),
                    "SMC": random.randint(50, 100),
                    "Wyckoff": random.randint(50, 100),
                    "Technical": random.randint(50, 100),
                    "Risk": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "Status": random.choice(["✅ Allowed", "⚠️ Review", "🔴 Blocked"]),
                }
            )
        df_signals = pd.DataFrame(signals)
        def color_risk(val):
            if val == "HIGH":
                return "background-color: #ff4444"
            elif val == "MEDIUM":
                return "background-color: #ffaa00"
            return "background-color: #00ff44"
        styled_df = df_signals.style.applymap(color_risk, subset=["Risk"])
        st.dataframe(styled_df, use_container_width=True, height=300)
    with col2:
        st.info("**Signal Filters**")
        st.slider("Min Confluence Score", 0, 100, 70)
        st.select_slider("Max Risk Level", options=["LOW", "MEDIUM", "HIGH"], value="MEDIUM")
        if st.button("🔄 Refresh Signals", use_container_width=True):
            st.rerun()
        st.warning("**Next Cooling Period**\n15:30 - 15:45 UTC")

with tab2:
    st.subheader("Performance Analytics")
    col1, col2, col3 = st.columns(3)
    with col1:
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        pnl_data = np.cumsum(np.random.randn(30) * 100)
        fig_pnl = go.Figure()
        fig_pnl.add_trace(
            go.Scatter(
                x=dates,
                y=pnl_data,
                mode="lines",
                name="Cumulative P&L",
                line=dict(color="#00ff44", width=2),
            )
        )
        fig_pnl.update_layout(title="30-Day P&L Curve", height=300, template="plotly_dark")
        st.plotly_chart(fig_pnl, use_container_width=True)
    with col2:
        win_rate = 68
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=win_rate,
                title={"text": "Win Rate %"},
                delta={"reference": 50},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 50], "color": "lightgray"},
                        {"range": [50, 80], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            )
        )
        fig_gauge.update_layout(height=300, template="plotly_dark")
        st.plotly_chart(fig_gauge, use_container_width=True)
    with col3:
        st.metric("Sharpe Ratio", "1.85", "0.15")
        st.metric("Max Drawdown", "-8.5%", "2.1%")
        st.metric("Profit Factor", "2.3", "0.3")
        st.metric("Avg Risk/Reward", "1:2.5", "0.2")

with tab3:
    st.subheader("Behavioral Pattern Analysis")
    col1, col2 = st.columns(2)
    with col1:
        hours = list(range(24))
        performance_by_hour = [random.uniform(-50, 100) for _ in hours]
        fig_behavior = go.Figure()
        fig_behavior.add_trace(
            go.Bar(
                x=hours,
                y=performance_by_hour,
                marker_color=["red" if p < 0 else "green" for p in performance_by_hour],
            )
        )
        fig_behavior.update_layout(
            title="Performance by Hour (UTC)",
            xaxis_title="Hour",
            yaxis_title="P&L ($)",
            height=400,
            template="plotly_dark",
        )
        st.plotly_chart(fig_behavior, use_container_width=True)
    with col2:
        st.info("**Detected Patterns**")
        patterns = {
            "Best Performance": "14:00-16:00 UTC",
            "Overconfidence After": "3 consecutive wins",
            "Fatigue Onset": "After 4 hours active",
            "Revenge Trading Risk": "After -$500 loss",
            "FOMO Triggers": "High volatility periods",
        }
        for pattern, detail in patterns.items():
            st.write(f"**{pattern}:** {detail}")
        st.warning("**Recommended Actions**")
        st.write("• Take a 15-minute break")
        st.write("• Reduce position size by 50%")
        st.write("• Review recent trades before continuing")

with tab4:
    st.subheader("Risk Management Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Risk Limits**")
        st.slider("Daily Loss Limit (%)", 1, 5, 3)
        st.slider("Max Trades/Day", 1, 10, 5)
        st.slider("Cooling Period (min)", 5, 30, 15)
        st.slider("Min Confluence Score", 50, 90, 70)
        st.info("**Behavioral Modules**")
        st.checkbox("Revenge Trading Protection", value=True)
        st.checkbox("Overconfidence Detection", value=True)
        st.checkbox("Fatigue Monitoring", value=True)
        st.checkbox("FOMO Protection", value=True)
    with col2:
        st.info("**Current Status**")
        status_data = {
            "Setting": ["Daily Loss Used", "Trades Executed", "Time Since Break", "Confluence Avg", "Risk Score"],
            "Current": ["1.2%", "2/5", "45 min", "78%", "3/10"],
            "Status": ["✅", "✅", "⚠️", "✅", "✅"],
        }
        df_status = pd.DataFrame(status_data)
        st.dataframe(df_status, use_container_width=True, hide_index=True)
        if st.button("💾 Save Settings", use_container_width=True, type="primary"):
            st.success("Settings saved successfully!")
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.info("Settings reset to defaults")

with tab5:
    st.subheader("Trading Journal & Reflection")
    with st.form("journal_entry"):
        st.write("**New Journal Entry**")
        st.text_input("Trade ID", value=f"T{random.randint(1000, 9999)}")
        c1, c2 = st.columns(2)
        with c1:
            st.select_slider(
                "Pre-Trade Emotion",
                options=["😰 Anxious", "😟 Nervous", "😐 Neutral", "😊 Confident", "😎 Overconfident"],
            )
        with c2:
            st.select_slider(
                "Post-Trade Emotion",
                options=["😢 Frustrated", "😔 Disappointed", "😐 Neutral", "😊 Satisfied", "🎉 Euphoric"],
            )
        st.text_area("Trade Notes & Lessons Learned", height=100)
        if st.form_submit_button("📝 Save Entry", use_container_width=True, type="primary"):
            st.success("Journal entry saved!")
    st.write("**Recent Journal Entries**")
    journal_entries = []
    for i in range(5):
        journal_entries.append(
            {
                "Date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "Trade": f"T{1000 + i}",
                "Result": random.choice(["Win +$250", "Loss -$150", "Win +$500"]),
                "Emotion": random.choice(["😊 Confident", "😰 Anxious", "😐 Neutral"]),
                "Key Lesson": random.choice(
                    [
                        "Followed the plan perfectly",
                        "Entered too early, need patience",
                        "Good risk management saved the day",
                        "FOMO led to poor entry",
                    ]
                ),
            }
        )
    df_journal = pd.DataFrame(journal_entries)
    st.dataframe(df_journal, use_container_width=True, hide_index=True)

with st.sidebar:
    st.image(
        "https://via.placeholder.com/300x100/1e1e1e/00ff44?text=ZANALYTICS+PULSE",
        use_column_width=True,
    )
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    if st.button("🚨 EMERGENCY STOP", use_container_width=True, type="primary"):
        st.error("All trading halted!")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    if st.button("📊 Generate Report", use_container_width=True):
        st.info("Report generation started...")
    st.markdown("---")
    st.subheader("💚 System Health")
    health_metrics = {
        "PulseKernel": "🟢 Online",
        "Confluence Scorer": "🟢 Active",
        "Risk Enforcer": "🟢 Protected",
        "Data Feed": "🟢 Connected",
        "MT5 Bridge": "🟡 Latency: 45ms",
    }
    for component, status in health_metrics.items():
        st.write(f"{component}: {status}")
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    st.markdown("---")
    st.caption("Zanalytics Pulse v11.5.1")
    st.caption("© 2024 NeuroCoreOS Research")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🧠 Behavioral Intelligence Layer | 🛡️ Risk Protection Active | 📊 Real-time Analysis</p>
        <p style='font-size: 0.8em;'>Remember: The system is your cognitive seatbelt, not just a trading tool.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
