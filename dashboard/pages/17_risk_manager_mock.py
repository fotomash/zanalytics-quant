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

# Page configuration
st.set_page_config(
    page_title="Risk Management Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
    }
    .risk-high { background-color: #ffebee; color: #c62828; }
    .risk-medium { background-color: #fff3e0; color: #ef6c00; }
    .risk-low { background-color: #e8f5e9; color: #2e7d32; }
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
            st.success("✅ MT5 Connected")
            st.json(tick_data)
        else:
            st.warning("⚠️ Using Mock Data")

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
