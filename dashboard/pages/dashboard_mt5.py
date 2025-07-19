import streamlit as st
import redis
import os
import json
import pandas as pd
from datetime import datetime
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="ZANFLOW Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize Redis connection
@st.cache_resource
def init_redis():
    try:
        host = os.environ.get("REDIS_HOST", "mm20.local")
        r = redis.Redis(host=host, port=6379, decode_responses=True)
        r.ping()
        return r
    except:
        st.error("❌ Redis not connected! Make sure Redis is running.")
        return None

# Get MT5 data from Redis
def get_mt5_data(r, symbol="XAUUSD"):
    if not r:
        return None

    try:
        # Get latest data
        key = f"mt5:{symbol}:latest"
        data = r.get(key)
        if data:
            return json.loads(data)
    except:
        pass
    return None

# Get historical data
def get_mt5_history(r, symbol="EURUSD", limit=50):
    if not r:
        return []

    try:
        key = f"mt5:{symbol}:history"
        history = r.lrange(key, 0, limit-1)
        return [json.loads(h) for h in history]
    except:
        return []

# Main dashboard
def main():
    st.title("🚀 ZANFLOW Trading Dashboard")
    st.markdown("Real-time MT5 Data Visualization")

    # Initialize Redis
    r = init_redis()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Symbol selection
        symbol = st.text_input("Symbol", value="EURUSD")

        # Refresh rate
        refresh_rate = st.slider("Refresh Rate (seconds)", 1, 10, 1)

        # Auto-refresh
        auto_refresh = st.checkbox("Auto Refresh", value=True)

        if st.button("🔄 Manual Refresh"):
            st.rerun()

    # Main content
    if r:
        # Get latest data
        latest_data = get_mt5_data(r, symbol)

        if latest_data:
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Bid",
                    f"{latest_data.get('bid', 0):.5f}",
                    delta=None
                )

            with col2:
                st.metric(
                    "Ask",
                    f"{latest_data.get('ask', 0):.5f}",
                    delta=None
                )

            with col3:
                spread = latest_data.get('spread', 0)
                st.metric("Spread", spread)

            with col4:
                timestamp = latest_data.get('timestamp', 0)
                dt = datetime.fromtimestamp(timestamp)
                st.metric("Last Update", dt.strftime("%H:%M:%S"))

            # ──────────────────────────────────────────────────────────────
            # Technical indicators summary
            # ──────────────────────────────────────────────────────────────
            if 'indicators' in latest_data:
                st.subheader("📈 Technical Indicators (latest tick)")
                indicators = latest_data['indicators']

                ind_cols = st.columns(6)
                ind_map = {
                    "RSI": indicators.get("rsi", 0),
                    "MACD": indicators.get("macd", 0),
                    "MACD Signal": indicators.get("macd_signal", 0),
                    "ADX": indicators.get("adx", 0),
                    "CCI": indicators.get("cci", 0),
                    "ATR": indicators.get("atr", 0)
                }
                for col, (name, value) in zip(ind_cols, ind_map.items()):
                    with col:
                        st.metric(name, f"{value:.2f}")

                trend_cols = st.columns(2)
                with trend_cols[0]:
                    st.metric("Trend", indicators.get("trend", "—"))
                with trend_cols[1]:
                    st.metric("Momentum", indicators.get("momentum", "—"))

            # ──────────────────────────────────────────────────────────────
            # Enriched metrics
            # ──────────────────────────────────────────────────────────────
            if 'enriched' in latest_data:
                st.subheader("✨ Enriched Metrics")
                enriched = latest_data['enriched']

                enr_cols = st.columns(3)
                with enr_cols[0]:
                    st.metric("Volatility 1 min", f"{enriched.get('volatility_1min', 0):.4f}")
                with enr_cols[1]:
                    st.metric("Volatility 5 min", f"{enriched.get('volatility_5min', 0):.4f}")
                with enr_cols[2]:
                    st.metric("VWAP", f"{enriched.get('vwap', 0):.2f}")

                # Volume profile horizontal bar chart
                if enriched.get('volume_profile'):
                    st.subheader("📊 Volume Profile (current session)")
                    vp = enriched['volume_profile']
                    vp_levels = list(vp.keys())
                    vp_values = list(vp.values())

                    fig_vp = go.Figure(
                        go.Bar(
                            x=vp_values,
                            y=vp_levels,
                            orientation='h'
                        )
                    )
                    fig_vp.update_layout(
                        height=400,
                        xaxis_title="Volume",
                        yaxis_title="Price Range"
                    )
                    st.plotly_chart(fig_vp, use_container_width=True)
            # ──────────────────────────────────────────────────────────────

            # Account info
            if 'account' in latest_data:
                st.subheader("💰 Account Information")
                acc_col1, acc_col2, acc_col3, acc_col4 = st.columns(4)

                account = latest_data['account']
                with acc_col1:
                    st.metric("Balance", f"${account.get('balance', 0):,.2f}")
                with acc_col2:
                    st.metric("Equity", f"${account.get('equity', 0):,.2f}")
                with acc_col3:
                    st.metric("Margin", f"${account.get('margin', 0):,.2f}")
                with acc_col4:
                    st.metric("Free Margin", f"${account.get('free_margin', 0):,.2f}")

            # ──────────────────────────────────────────────────────────────
            # Candlestick chart
            # ──────────────────────────────────────────────────────────────
            if 'candles' in latest_data and latest_data['candles']:
                st.subheader("🕯️ Recent Price Candles")
                candles = sorted(latest_data['candles'], key=lambda c: c.get("time", 0))  # oldest → newest
                df_c = pd.DataFrame(candles)
                df_c['time'] = pd.to_datetime(df_c['time'], unit='s')

                fig_candles = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df_c['time'],
                            open=df_c['open'],
                            high=df_c['high'],
                            low=df_c['low'],
                            close=df_c['close'],
                            increasing_line_width=1,
                            decreasing_line_width=1
                        )
                    ]
                )
                fig_candles.update_layout(
                    height=400,
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                st.plotly_chart(fig_candles, use_container_width=True)
            # Price chart
            st.subheader("📊 Price History")

            # Get historical data
            history = get_mt5_history(r, symbol)

            if history:
                # Create DataFrame
                df_data = []
                for h in history:
                    df_data.append({
                        'time': datetime.fromtimestamp(h.get('timestamp', 0)),
                        'bid': h.get('bid', 0),
                        'ask': h.get('ask', 0),
                        'spread': h.get('spread', 0)
                    })

                df = pd.DataFrame(df_data)

                if not df.empty:
                    # Create chart
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        row_heights=[0.7, 0.3]
                    )

                    # Price chart
                    fig.add_trace(
                        go.Scatter(
                            x=df['time'], 
                            y=df['bid'],
                            name='Bid',
                            line=dict(color='blue', width=2)
                        ),
                        row=1, col=1
                    )

                    fig.add_trace(
                        go.Scatter(
                            x=df['time'], 
                            y=df['ask'],
                            name='Ask',
                            line=dict(color='red', width=2)
                        ),
                        row=1, col=1
                    )

                    # Spread chart
                    fig.add_trace(
                        go.Scatter(
                            x=df['time'], 
                            y=df['spread'],
                            name='Spread',
                            line=dict(color='green', width=2)
                        ),
                        row=2, col=1
                    )

                    # Update layout
                    fig.update_layout(
                        height=600,
                        showlegend=True,
                        xaxis_rangeslider_visible=False
                    )

                    fig.update_xaxes(title_text="Time", row=2, col=1)
                    fig.update_yaxes(title_text="Price", row=1, col=1)
                    fig.update_yaxes(title_text="Spread", row=2, col=1)

                    st.plotly_chart(fig, use_container_width=True)

            # Raw data display
            with st.expander("🔍 View Raw Data"):
                st.json(latest_data)

        else:
            st.warning(f"⏳ Waiting for data from MT5 for {symbol}...")
            st.info("Make sure the EA is running on MT5 and sending data.")

    else:
        st.error("❌ Cannot connect to Redis. Please check if Redis is running.")

    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

if __name__ == "__main__":
    main()
