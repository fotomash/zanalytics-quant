"""
Risk Management Dashboard - Simplified Version
Works with mock data when MT5 is not available
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import redis
import json
import time
import os
import urllib.parse as urlparse
from typing import Dict, List, Optional
import requests
import base64

# Page configuration
st.set_page_config(
    page_title="Risk Management Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper for background image
def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# CSS and background (copied from Macro Intelligence page)
img_base64 = get_base64_image("./pages/image_af247b.jpg")
st.markdown(f"""
<style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}
    .main, .block-container {{
        background: rgba(14, 17, 23, 0.88) !important;
        border-radius: 16px;
        padding: 2.2rem 2.4rem;
        box-shadow: 0 4px 32px 0 rgba(12,10,30,0.16);
    }}
    .market-card {{
        background: rgba(28, 28, 32, 0.83);
        border-radius: 14px;
        padding: 24px 24px 14px 24px;
        border: 1.4px solid rgba(255,255,255,0.09);
        margin-bottom: 24px;
        box-shadow: 0 2px 14px 0 rgba(0,0,0,0.23);
    }}
</style>
""", unsafe_allow_html=True)

class RiskManager:
    """Risk Management with MT5 API fallback"""

    def __init__(self):
        self.mt5_url = os.getenv("MT5_URL", "http://mt5:5001")
        self.django_url = os.getenv("DJANGO_URL", "http://django:8000")

        # Try to connect to Redis (inside Docker network use service name "redis")
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
        except Exception as e:
            self.redis_client = None
            st.warning(f"Redis not available ({e}) - using local storage")

    def get_mt5_data(self, endpoint: str) -> Optional[Dict]:
        """Get data from MT5 API"""
        try:
            response = requests.get(f"{self.mt5_url}/{endpoint}", timeout=2)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def get_account_info(self) -> Dict:
        """Get account info from MT5 or use mock data"""
        # Try MT5 API first
        mt5_data = self.get_mt5_data("account_info")
        if mt5_data:
            return mt5_data

        # Fallback to mock data
        return {
            'login': os.getenv('MT5_LOGIN', '1511516399'),
            'server': os.getenv('MT5_SERVER', 'FTMO-Demo'),
            'balance': 100000.00,
            'equity': 98500.00 + np.random.uniform(-500, 500),
            'margin': 2500.00,
            'free_margin': 96000.00,
            'margin_level': 3940.00,
            'profit': -1500.00 + np.random.uniform(-100, 100),
            'leverage': 100,
            'currency': 'USD',
        }

    def get_tick_data(self, symbol: str = "EURUSD") -> Optional[Dict]:
        """Get tick data from MT5"""
        tick_data = self.get_mt5_data(f"symbol_info_tick/{symbol}")
        if tick_data:
            return tick_data

        # Mock tick data
        return {
            'symbol': symbol,
            'bid': 1.0850 + np.random.uniform(-0.001, 0.001),
            'ask': 1.0852 + np.random.uniform(-0.001, 0.001),
            'last': 1.0851,
            'volume': np.random.randint(100, 1000),
            'time': datetime.now().isoformat()
        }

    def get_positions(self) -> pd.DataFrame:
        """Get positions from MT5 or generate mock"""
        positions_data = self.get_mt5_data("positions_get")

        if positions_data and isinstance(positions_data, list):
            return pd.DataFrame(positions_data)

        # Mock positions
        positions = []
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        for i in range(np.random.randint(0, 4)):
            positions.append({
                'ticket': 1000000 + i,
                'symbol': np.random.choice(symbols),
                'type': np.random.choice(['BUY', 'SELL']),
                'volume': round(np.random.uniform(0.01, 1.0), 2),
                'price_open': round(np.random.uniform(1.0, 1.5), 5),
                'price_current': round(np.random.uniform(1.0, 1.5), 5),
                'profit': round(np.random.uniform(-500, 500), 2),
                'time': datetime.now() - timedelta(hours=np.random.randint(1, 24))
            })

        return pd.DataFrame(positions)

    def get_recent_trades(self, limit: int = 10, days: int = 7) -> pd.DataFrame:
        """
        Try MT5 HTTP bridge endpoints for recent trades; fall back to mock data.
        Expected endpoints (any available is fine):
          - history_deals_get?days={days}&limit={limit}
          - history_orders_get?days={days}&limit={limit}
        """
        candidates = [
            f"history_deals_get?days={days}&limit={limit}",
            f"history_orders_get?days={days}&limit={limit}",
            # ISO window try (some bridges use from/to)
            f"history_deals_get?from={(datetime.now()-timedelta(days=days)).isoformat()}&to={datetime.now().isoformat()}&limit={limit}"
        ]
        for ep in candidates:
            data = self.get_mt5_data(ep)
            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                # normalize time column
                time_cols = [c for c in ["time", "time_msc", "time_done", "time_close"] if c in df.columns]
                if time_cols:
                    col = time_cols[0]
                    try:
                        df["time"] = pd.to_datetime(df[col], unit="s", errors="coerce")
                    except Exception:
                        df["time"] = pd.to_datetime(df[col], errors="coerce")
                elif "timestamp" in df.columns:
                    df["time"] = pd.to_datetime(df["timestamp"], errors="coerce")
                if "type" in df.columns:
                    df["type"] = df["type"].replace({0: "BUY", 1: "SELL", 2: "BUY", 3: "SELL"})
                cols = [c for c in ["time","ticket","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in df.columns]
                if "time" in cols:
                    df = df.sort_values("time", ascending=False)
                return df[cols].head(limit) if cols else df.head(limit)

        # Fallback mock
        mock = []
        symbols = ["EURUSD","GBPUSD","USDJPY","XAUUSD"]
        for i in range(min(limit, 8)):
            mock.append({
                "time": datetime.now() - timedelta(hours=i*3 + np.random.randint(0,2)),
                "ticket": 1000000 + i,
                "symbol": np.random.choice(symbols),
                "type": np.random.choice(["BUY","SELL"]),
                "volume": round(np.random.uniform(0.05, 1.00), 2),
                "price": round(np.random.uniform(1.05, 1.35), 5),
                "profit": round(np.random.uniform(-350, 420), 2),
                "comment": "mock"
            })
        return pd.DataFrame(mock)

    def calculate_risk_metrics(self, account_info: Dict, positions_df: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        balance = account_info.get('balance', 100000)
        equity = account_info.get('equity', 100000)

        metrics = {
            'account_risk': 0,
            'position_risk': 0,
            'drawdown': 0,
            'risk_score': 0,
            'daily_loss': 0,
            'max_daily_loss_limit': 5.0,  # 5% daily loss limit
            'max_total_loss_limit': 10.0,  # 10% total loss limit
        }

        if balance > 0:
            # Calculate drawdown
            metrics['drawdown'] = ((balance - equity) / balance) * 100

            # Calculate account risk
            metrics['account_risk'] = max(0, (1 - (equity / balance)) * 100)

            # Calculate position risk
            if not positions_df.empty:
                total_risk = abs(positions_df['profit'].sum())
                metrics['position_risk'] = (total_risk / balance) * 100

            # Calculate risk score (0-100)
            risk_factors = [
                min(metrics['drawdown'] * 2, 30),
                min(metrics['account_risk'] * 2, 30),
                min(metrics['position_risk'] * 2, 40),
            ]
            metrics['risk_score'] = sum(risk_factors)

        # Store in Redis if available
        if self.redis_client:
            try:
                self.redis_client.hset(
                    f"risk_metrics:{datetime.now().strftime('%Y%m%d_%H')}",
                    mapping={k: str(v) for k, v in metrics.items()}
                )
                self.redis_client.expire(f"risk_metrics:{datetime.now().strftime('%Y%m%d_%H')}", 86400)
            except:
                pass

        return metrics

    def get_historical_metrics(self, hours: int = 24) -> pd.DataFrame:
        """Get historical risk metrics from Redis"""
        if not self.redis_client:
            # Generate mock historical data
            data = []
            for i in range(hours):
                timestamp = datetime.now() - timedelta(hours=i)
                data.append({
                    'timestamp': timestamp,
                    'risk_score': 50 + np.random.uniform(-20, 20),
                    'drawdown': 2 + np.random.uniform(-1, 3),
                    'equity': 100000 + np.random.uniform(-5000, 5000)
                })
            return pd.DataFrame(data)

        # Try to get from Redis
        try:
            data = []
            for i in range(hours):
                timestamp = datetime.now() - timedelta(hours=i)
                key = f"risk_metrics:{timestamp.strftime('%Y%m%d_%H')}"
                metrics = self.redis_client.hgetall(key)
                if metrics:
                    metrics['timestamp'] = timestamp
                    data.append(metrics)

            if data:
                return pd.DataFrame(data)
        except:
            pass

        # Fallback to mock
        return self.get_historical_metrics(hours)

def create_gauge_chart(value: float, title: str, max_value: float = 100) -> go.Figure:
    """Create a gauge chart"""
    color = "green" if value < 30 else "yellow" if value < 70 else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': "lightgray"},
                {'range': [30, 70], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(height=250)
    return fig

def main():
    """Main dashboard function"""

    st.title("🛡️ Risk Management Dashboard")

    # Data-source banner: show account number and broker if available
    acct_info = {}
    try:
        if 'risk_manager' in st.session_state:
            acct_info = st.session_state.risk_manager.get_account_info()
    except Exception:
        acct_info = {}
    login = acct_info.get('login')
    broker = acct_info.get('server') or acct_info.get('company')
    if login:
        st.markdown(
            f'''
            <div class="market-card" style="text-align:center;">
                <span style="background: #99ffd0; color:#181818; padding:8px 14px; border-radius:12px; font-weight:800;">
                    Account {login} • {broker or '—'}
                </span>
            </div>
            ''',
            unsafe_allow_html=True
        )
    st.markdown("### Real-time Account Monitoring & Risk Control")

    # Initialize Risk Manager
    if 'risk_manager' not in st.session_state:
        st.session_state.risk_manager = RiskManager()

    risk_manager = st.session_state.risk_manager

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Connection status
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh"):
                st.rerun()

        with col2:
            auto_refresh = st.checkbox("Auto", value=False)

        if auto_refresh:
            refresh_interval = st.slider("Interval (sec)", 1, 60, 5)

        # Risk limits
        st.header("⚠️ Risk Limits")
        daily_loss_limit = st.slider("Daily Loss %", 1.0, 10.0, 5.0)
        max_drawdown = st.slider("Max Drawdown %", 5.0, 20.0, 10.0)
        max_positions = st.number_input("Max Positions", 1, 20, 5)

        # Data source indicator
        st.header("📡 Data Source")
        tick_data = risk_manager.get_tick_data()
        if tick_data:
            st.success("✅ Real MetaTrader account (HTTP bridge)")
            with st.expander("Latest Tick", expanded=False):
                st.json(tick_data)
        else:
            st.warning("⚠️ Using mock data (bridge unavailable)")

    # Get data
    account_info = risk_manager.get_account_info()
    positions_df = risk_manager.get_positions()
    risk_metrics = risk_manager.calculate_risk_metrics(account_info, positions_df)

    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "💰 Balance",
            f"${account_info.get('balance', 0):,.2f}",
            f"${account_info.get('profit', 0):,.2f}"
        )

    with col2:
        st.metric(
            "📊 Equity",
            f"${account_info.get('equity', 0):,.2f}",
            f"{((account_info.get('equity', 0) / account_info.get('balance', 1) - 1) * 100):.2f}%"
        )

    with col3:
        st.metric(
            "🎯 Margin Level",
            f"{account_info.get('margin_level', 0):,.0f}%",
            "Safe" if account_info.get('margin_level', 0) > 200 else "Warning"
        )

    with col4:
        st.metric(
            "📈 Profit/Loss",
            f"${account_info.get('profit', 0):,.2f}",
            f"{(account_info.get('profit', 0) / account_info.get('balance', 1) * 100):.2f}%"
        )

    with col5:
        st.metric(
            "🔢 Positions",
            len(positions_df),
            f"Max: {max_positions}"
        )

    # Risk gauges
    st.markdown("---")
    st.subheader("🎯 Risk Metrics")

    gauge_cols = st.columns(4)

    with gauge_cols[0]:
        fig = create_gauge_chart(risk_metrics['risk_score'], "Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_cols[1]:
        fig = create_gauge_chart(risk_metrics['drawdown'], "Drawdown %")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_cols[2]:
        fig = create_gauge_chart(risk_metrics['account_risk'], "Account Risk %")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_cols[3]:
        fig = create_gauge_chart(risk_metrics['position_risk'], "Position Risk %")
        st.plotly_chart(fig, use_container_width=True)

    # Positions table
    if not positions_df.empty:
        st.markdown("---")
        st.subheader("📋 Open Positions")
        st.dataframe(positions_df, use_container_width=True)

    # Recent Trades section (before Historical Metrics)
    st.markdown("---")
    st.subheader("📜 Recent Trades")
    recent_trades = risk_manager.get_recent_trades(limit=10, days=7)
    if isinstance(recent_trades, pd.DataFrame) and not recent_trades.empty:
        display_cols = [c for c in ["time","ticket","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in recent_trades.columns]
        df_show = recent_trades[display_cols].copy() if display_cols else recent_trades.copy()
        if "time" in df_show.columns:
            df_show["time"] = pd.to_datetime(df_show["time"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df_show, use_container_width=True)
    else:
        st.info("No recent trades returned by the bridge.")

    # Historical chart
    st.markdown("---")
    st.subheader("📈 Historical Metrics")

    historical_df = risk_manager.get_historical_metrics(24)

    if not historical_df.empty:
        # Create tabs
        tab1, tab2 = st.tabs(["Risk Score", "Equity"])

        with tab1:
            fig = px.line(
                historical_df,
                x='timestamp',
                y='risk_score',
                title='Risk Score Over Time',
                labels={'risk_score': 'Risk Score', 'timestamp': 'Time'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = px.line(
                historical_df,
                x='timestamp',
                y='equity',
                title='Equity Over Time',
                labels={'equity': 'Equity ($)', 'timestamp': 'Time'}
            )
            st.plotly_chart(fig, use_container_width=True)

    # Risk warnings
    st.markdown("---")
    st.subheader("⚠️ Risk Status")

    warnings = []

    if risk_metrics['drawdown'] > max_drawdown:
        warnings.append(f"🔴 Drawdown exceeds limit: {risk_metrics['drawdown']:.2f}% > {max_drawdown}%")

    if risk_metrics['risk_score'] > 70:
        warnings.append(f"🔴 High risk score: {risk_metrics['risk_score']:.1f}/100")

    if len(positions_df) > max_positions:
        warnings.append(f"🟡 Too many positions: {len(positions_df)} > {max_positions}")

    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("✅ All risk parameters within limits")

    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
