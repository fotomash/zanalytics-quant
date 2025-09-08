import streamlit as st
import redis
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os

st.set_page_config(page_title="ZAnalytics Trading Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.alert-box {
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
.alert-warning {
    background-color: #fff3cd;
    border: 1px solid #ffeeba;
}
.alert-success {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
}
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_resource
def init_redis():
    redis_host = os.getenv("REDIS_HOST", "redis")  # default to 'redis' for Docker
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        return redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
    except Exception:
        return redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    
redis_client = init_redis()
redis_stream = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0)

st.sidebar.title("🎛️ Dashboard Controls")
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 30, 5)

available_symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
selected_symbols = st.sidebar.multiselect("Select Symbols", available_symbols, default=available_symbols)

timeframe = st.sidebar.selectbox("Timeframe", ['1m', '5m', '15m', '1h'], index=1)

show_account = st.sidebar.checkbox("Show Account Info", value=True)
show_positions = st.sidebar.checkbox("Show Positions", value=True)
show_market = st.sidebar.checkbox("Show Market Data", value=True)
show_alerts = st.sidebar.checkbox("Show Alerts", value=True)
show_analytics = st.sidebar.checkbox("Show Analytics", value=True)

st.title("📊 ZAnalytics Unified Trading Dashboard")

# --- Decision Bar (top row) ---------------------------------------------------
import requests, contextlib

BASE = os.getenv("PULSE_BASE_URL") or os.getenv("DJANGO_API_URL", "http://django:8000")
BASE = str(BASE).rstrip("/") + "/api/pulse"

@st.cache_data(ttl=2.0, show_spinner=False)
def _get_json(url: str, method: str = "GET", payload=None, timeout: float = 1.0, default=None):
    try:
        if method.upper() == "POST":
            r = requests.post(url, json=(payload or {}), timeout=timeout)
        else:
            r = requests.get(url, timeout=timeout)
        return r.json() if r.ok else (default if default is not None else {})
    except Exception:
        return default if default is not None else {}

def decision_bar():
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.4, 1, 1, 1.4])
        # 1) Confluence Score snapshot
        score = _get_json(f"{BASE}/score/peek", method="POST", default={})
        c1.metric("Confluence Score", score.get("score", "—"), score.get("grade", ""))
        # 2) Risk summary
        risk = _get_json(f"{BASE}/risk/summary", default={})
        c2.metric("Risk Left", risk.get("risk_left", "—"))
        c3.metric("Trades Left", risk.get("trades_left", "—"))
        # 3) Adapter health / latency
        adapter = _get_json(f"{BASE}/adapter/status", default={})
        lag = adapter.get("lag_ms", "—")
        fps = adapter.get("fps")
        status = adapter.get("status") or "down"
        c4.metric("Kernel/Adapter", f"{status}", f"lag {lag} ms" + (f" • {float(fps):.1f} fps" if isinstance(fps, (int, float)) else ""))
        # Explain reasons
        reasons = score.get("reasons") or []
        if reasons:
            with st.expander("Explain"):
                for r in reasons:
                    st.write(f"• {r}")
        # Optional warnings
        warns = risk.get("warnings") or []
        if warns:
            st.warning(" / ".join([str(w) for w in warns]))

decision_bar()

# Footer legal links (public URLs for policy pages)
with st.container():
    st.caption(
        "—  "
        "[Privacy Policy](/Privacy%20Policy)  ·  "
        "[Terms of Use](/Terms%20of%20Use)"
    )

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

if show_account:
    st.header("💰 Account Information")
    account_data = redis_client.get('account_info')
    if account_data:
        account = json.loads(account_data)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Balance", f"${account['balance']:,.2f}")
        col2.metric("Equity", f"${account['equity']:,.2f}")
        col3.metric("Free Margin", f"${account['free_margin']:,.2f}")
        col4.metric("Floating P&L", f"${account['profit']:,.2f}", delta=f"{(account['profit']/account['balance']*100):.2f}%")
    else:
        st.warning("No account data available")

if show_positions:
    st.header("📈 Open Positions")
    positions_data = redis_client.get('open_positions')
    if positions_data:
        positions = json.loads(positions_data)
        if positions:
            df_positions = pd.DataFrame(positions)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Positions", len(positions))
            total_profit = sum(p['profit'] for p in positions)
            col2.metric("Total P&L", f"${total_profit:,.2f}")
            total_volume = sum(p['volume'] for p in positions)
            col3.metric("Total Volume", f"{total_volume:.2f}")
            st.dataframe(df_positions[['ticket', 'symbol', 'type', 'volume', 'price_open', 'price_current', 'profit']], use_container_width=True)
            profit_by_symbol = df_positions.groupby('symbol')['profit'].sum()
            fig_profit = go.Figure(data=[go.Bar(x=profit_by_symbol.index, y=profit_by_symbol.values, marker_color=['green' if x > 0 else 'red' for x in profit_by_symbol.values])])
            fig_profit.update_layout(title="Profit by Symbol", height=300)
            st.plotly_chart(fig_profit, use_container_width=True)
        else:
            st.info("No open positions")
    else:
        st.warning("No position data available")

if show_market:
    st.header("📊 Market Data")
    if selected_symbols:
        tabs = st.tabs(selected_symbols)
        for i, symbol in enumerate(selected_symbols):
            with tabs[i]:
                col1, col2 = st.columns([2, 1])
                with col1:
                    latest_tick_data = redis_client.get(f"latest_tick:{symbol}")
                    if latest_tick_data:
                        tick = json.loads(latest_tick_data)
                        p1, p2, p3 = st.columns(3)
                        p1.metric("Bid", f"{tick['bid']:.5f}")
                        p2.metric("Ask", f"{tick['ask']:.5f}")
                        spread = float(tick['ask']) - float(tick['bid'])
                        p3.metric("Spread", f"{spread:.5f}")
                    stream_key = f"tick_stream:{symbol}"
                    ticks = redis_stream.xrevrange(stream_key, count=500)
                    if ticks:
                        tick_data = []
                        for msg_id, data in ticks:
                            d = {k.decode(): v.decode() for k, v in data.items()}
                            tick_data.append({'time': datetime.fromtimestamp(float(d['time'])), 'bid': float(d['bid']), 'ask': float(d['ask'])})
                        df_ticks = pd.DataFrame(tick_data).sort_values('time')
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df_ticks['time'], y=df_ticks['bid'], name='Bid', line=dict(color='blue')))
                        fig.add_trace(go.Scatter(x=df_ticks['time'], y=df_ticks['ask'], name='Ask', line=dict(color='red')))
                        fig.update_layout(title=f"{symbol} Live Prices", xaxis_title="Time", yaxis_title="Price", height=400)
                        st.plotly_chart(fig, use_container_width=True)
                with col2:
                    indicators_data = redis_client.get(f"latest_indicators:{symbol}:{timeframe}")
                    if indicators_data:
                        indicators = json.loads(indicators_data)
                        st.subheader("Technical Indicators")
                        for key, value in indicators.items():
                            if key.startswith('SMA') or key.startswith('RSI'):
                                st.metric(key, f"{value:.5f}")
                    agg_key = f"aggregate:{symbol}:{timeframe}"
                    latest_agg = redis_client.hgetall(agg_key)
                    if latest_agg:
                        latest_time = max(latest_agg.keys())
                        agg_data = json.loads(latest_agg[latest_time])
                        st.subheader(f"{timeframe} Statistics")
                        st.metric("High", f"{agg_data['high']:.5f}")
                        st.metric("Low", f"{agg_data['low']:.5f}")
                        st.metric("Volume", f"{agg_data['volume']:.0f}")
                        st.metric("Avg Spread", f"{agg_data['avg_spread']:.5f}")

if show_alerts:
    st.header("🚨 Recent Alerts")
    alerts = redis_stream.xrevrange('alerts_stream', count=20)
    if alerts:
        for msg_id, alert_data in alerts:
            alert = {k.decode(): v.decode() for k, v in alert_data.items()}
            if alert['type'] == 'stop_loss_warning':
                alert_class = "alert-warning"; icon = "⚠️"
            else:
                alert_class = "alert-success"; icon = "✅"
            st.markdown(f"<div class='alert-box {alert_class}'>{icon} {alert['message']}</div>", unsafe_allow_html=True)
    else:
        st.info("No recent alerts")

if show_analytics:
    st.header("📈 Analytics & Reports")
    col1, col2 = st.columns(2)
    with col1:
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_data = redis_client.get(f"daily_report:{report_date}")
        if report_data:
            report = json.loads(report_data)
            st.subheader("Today's Summary")
            if 'positions_summary' in report:
                st.metric("Total Positions", report['positions_summary']['total_positions'])
                st.metric("Total P&L", f"${report['positions_summary']['total_profit']:,.2f}")
            if 'alerts_summary' in report:
                st.metric("Stop Loss Warnings", report['alerts_summary']['stop_loss_warning'])
                st.metric("Take Profit Suggestions", report['alerts_summary']['take_profit_suggestion'])
    with col2:
        if 'symbol_statistics' in report and report['symbol_statistics']:
            st.subheader("Symbol Performance")
            symbols = list(report['symbol_statistics'].keys())
            volumes = [stats['total_volume'] for stats in report['symbol_statistics'].values()]
            fig_volume = go.Figure(data=[go.Pie(labels=symbols, values=volumes, hole=0.4)])
            fig_volume.update_layout(title="Volume Distribution", height=300)
            st.plotly_chart(fig_volume, use_container_width=True)
    st.subheader("Historical Performance")
    historical_reports = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        rep_data = redis_client.get(f"daily_report:{date}")
        if rep_data:
            rep = json.loads(rep_data)
            if 'account' in rep:
                historical_reports.append({'date': date, 'balance': rep['account']['balance'], 'equity': rep['account']['equity']})
    if historical_reports:
        df_history = pd.DataFrame(historical_reports)
        df_history['date'] = pd.to_datetime(df_history['date'])
        df_history = df_history.sort_values('date')
        fig_history = go.Figure()
        fig_history.add_trace(go.Scatter(x=df_history['date'], y=df_history['balance'], name='Balance', line=dict(color='blue', width=2)))
        fig_history.add_trace(go.Scatter(x=df_history['date'], y=df_history['equity'], name='Equity', line=dict(color='green', width=2)))
        fig_history.update_layout(title="Account Balance History", xaxis_title="Date", yaxis_title="Amount ($)", height=400)
        st.plotly_chart(fig_history, use_container_width=True)

st.markdown("---")
st.markdown(f"<div style='text-align: center; color: #666;'>ZAnalytics Trading Dashboard | Real-time data from Redis | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
