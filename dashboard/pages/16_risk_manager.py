"""
Risk Management Dashboard - 16_risk_manager.py
Real-time MT5 account monitoring and risk management
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import redis
import json
import time
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Risk Management Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .risk-metric {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-high { background-color: #ffebee; color: #c62828; }
    .risk-medium { background-color: #fff3e0; color: #ef6c00; }
    .risk-low { background-color: #e8f5e9; color: #2e7d32; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

class MT5RiskManager:
    """MT5 Account and Risk Management"""

    def __init__(self):
        self.mt5_login = int(os.getenv('MT5_LOGIN', '1511516399'))
        self.mt5_password = os.getenv('MT5_PASSWORD', 'ih*2Q?8!m?')
        self.mt5_server = os.getenv('MT5_SERVER', 'FTMO-Demo')
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.connected = False

    def connect(self) -> bool:
        """Connect to MT5"""
        try:
            if not mt5.initialize():
                return False

            authorized = mt5.login(
                login=self.mt5_login,
                password=self.mt5_password,
                server=self.mt5_server
            )

            if authorized:
                self.connected = True
                return True
            return False
        except Exception as e:
            st.error(f"MT5 Connection Error: {e}")
            return False

    def get_account_info(self) -> Dict:
        """Get account information"""
        if not self.connected:
            self.connect()

        account_info = mt5.account_info()
        if account_info is None:
            return {}

        return {
            'login': account_info.login,
            'server': account_info.server,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'margin_level': account_info.margin_level,
            'profit': account_info.profit,
            'leverage': account_info.leverage,
            'currency': account_info.currency,
            'name': account_info.name,
            'company': account_info.company,
        }

    def get_positions(self) -> pd.DataFrame:
        """Get all open positions"""
        if not self.connected:
            self.connect()

        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['time_update'] = pd.to_datetime(df['time_update'], unit='s')
        return df

    def get_history(self, days: int = 30) -> pd.DataFrame:
        """Get trading history"""
        if not self.connected:
            self.connect()

        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now()

        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None or len(deals) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def calculate_risk_metrics(self, account_info: Dict, positions_df: pd.DataFrame) -> Dict:
        """Calculate risk metrics"""
        metrics = {
            'account_risk': 0,
            'position_risk': 0,
            'drawdown': 0,
            'risk_score': 0,
            'daily_loss': 0,
            'max_daily_loss_limit': 0.05,  # 5% daily loss limit
            'max_total_loss_limit': 0.10,  # 10% total loss limit
        }

        if not account_info:
            return metrics

        balance = account_info.get('balance', 0)
        equity = account_info.get('equity', 0)

        if balance > 0:
            # Calculate drawdown
            metrics['drawdown'] = ((balance - equity) / balance) * 100

            # Calculate account risk
            metrics['account_risk'] = (1 - (equity / balance)) * 100

            # Calculate position risk
            if not positions_df.empty:
                total_risk = positions_df['profit'].sum()
                metrics['position_risk'] = abs(total_risk / balance) * 100

            # Calculate risk score (0-100)
            risk_factors = [
                min(metrics['drawdown'] * 2, 30),  # Drawdown weight: 30%
                min(metrics['account_risk'] * 2, 30),  # Account risk weight: 30%
                min(metrics['position_risk'] * 2, 40),  # Position risk weight: 40%
            ]
            metrics['risk_score'] = sum(risk_factors)

        # Store in Redis for historical tracking
        self.redis_client.hset(
            f"risk_metrics:{datetime.now().strftime('%Y%m%d')}",
            mapping={k: str(v) for k, v in metrics.items()}
        )

        return metrics

    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics"""
        history_df = self.get_history(days=1)

        if history_df.empty:
            return {
                'trades_today': 0,
                'profit_today': 0,
                'loss_today': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
            }

        # Filter for today's trades
        today = datetime.now().date()
        today_trades = history_df[history_df['time'].dt.date == today]

        profits = today_trades[today_trades['profit'] > 0]['profit']
        losses = today_trades[today_trades['profit'] < 0]['profit']

        return {
            'trades_today': len(today_trades),
            'profit_today': profits.sum() if not profits.empty else 0,
            'loss_today': abs(losses.sum()) if not losses.empty else 0,
            'win_rate': (len(profits) / len(today_trades) * 100) if len(today_trades) > 0 else 0,
            'avg_profit': profits.mean() if not profits.empty else 0,
            'avg_loss': abs(losses.mean()) if not losses.empty else 0,
        }

def create_gauge_chart(value: float, title: str, max_value: float = 100) -> go.Figure:
    """Create a gauge chart for risk metrics"""

    # Determine color based on value
    if value < 30:
        color = "green"
    elif value < 70:
        color = "yellow"
    else:
        color = "red"

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
    st.markdown("### Real-time MT5 Account Monitoring & Risk Control")

    # Initialize Risk Manager
    if 'risk_manager' not in st.session_state:
        st.session_state.risk_manager = MT5RiskManager()

    risk_manager = st.session_state.risk_manager

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Controls")

        # Connection status
        if st.button("🔌 Connect to MT5"):
            if risk_manager.connect():
                st.success("✅ Connected to MT5")
            else:
                st.error("❌ Failed to connect")

        # Refresh settings
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 60, 5)

        # Risk limits
        st.header("⚠️ Risk Limits")
        daily_loss_limit = st.slider("Daily Loss Limit (%)", 1, 10, 5)
        max_drawdown = st.slider("Max Drawdown (%)", 5, 20, 10)
        max_positions = st.number_input("Max Open Positions", 1, 20, 5)

        # Display settings
        st.header("📊 Display Settings")
        show_positions = st.checkbox("Show Open Positions", value=True)
        show_history = st.checkbox("Show Trade History", value=True)
        history_days = st.slider("History Days", 1, 90, 30)

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

    # Get account information
    account_info = risk_manager.get_account_info()
    positions_df = risk_manager.get_positions()
    risk_metrics = risk_manager.calculate_risk_metrics(account_info, positions_df)
    daily_stats = risk_manager.get_daily_stats()

    # Top metrics row
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
            f"{account_info.get('margin_level', 0):,.2f}%",
            "Safe" if account_info.get('margin_level', 0) > 200 else "Warning"
        )

    with col4:
        st.metric(
            "📈 Today's P&L",
            f"${daily_stats['profit_today'] - daily_stats['loss_today']:,.2f}",
            f"{daily_stats['win_rate']:.1f}% Win Rate"
        )

    with col5:
        st.metric(
            "🔢 Open Positions",
            len(positions_df),
            f"Max: {max_positions}"
        )

    # Risk gauges
    st.markdown("---")
    st.subheader("🎯 Risk Metrics")

    gauge_col1, gauge_col2, gauge_col3, gauge_col4 = st.columns(4)

    with gauge_col1:
        fig = create_gauge_chart(risk_metrics['risk_score'], "Overall Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col2:
        fig = create_gauge_chart(risk_metrics['drawdown'], "Drawdown %")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col3:
        fig = create_gauge_chart(risk_metrics['account_risk'], "Account Risk %")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col4:
        fig = create_gauge_chart(risk_metrics['position_risk'], "Position Risk %")
        st.plotly_chart(fig, use_container_width=True)

    # Open positions table
    if show_positions and not positions_df.empty:
        st.markdown("---")
        st.subheader("📋 Open Positions")

        # Format positions dataframe
        display_cols = ['ticket', 'symbol', 'type', 'volume', 'price_open', 
                       'price_current', 'profit', 'time']
        positions_display = positions_df[display_cols].copy()
        positions_display['type'] = positions_display['type'].map({0: 'BUY', 1: 'SELL'})

        # Color code profit/loss
        def color_profit(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'

        styled_positions = positions_display.style.applymap(
            color_profit, subset=['profit']
        )

        st.dataframe(styled_positions, use_container_width=True)

    # Trade history
    if show_history:
        st.markdown("---")
        st.subheader("📜 Trade History")

        history_df = risk_manager.get_history(days=history_days)

        if not history_df.empty:
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Chart", "🗂️ Details"])

            with tab1:
                # Summary statistics
                col1, col2, col3, col4 = st.columns(4)

                total_trades = len(history_df)
                profitable_trades = len(history_df[history_df['profit'] > 0])
                losing_trades = len(history_df[history_df['profit'] < 0])

                with col1:
                    st.metric("Total Trades", total_trades)

                with col2:
                    st.metric("Profitable", profitable_trades, 
                             f"{(profitable_trades/total_trades*100):.1f}%")

                with col3:
                    st.metric("Losing", losing_trades,
                             f"{(losing_trades/total_trades*100):.1f}%")

                with col4:
                    st.metric("Total P&L", f"${history_df['profit'].sum():,.2f}")

            with tab2:
                # Cumulative P&L chart
                history_df_sorted = history_df.sort_values('time')
                history_df_sorted['cumulative_profit'] = history_df_sorted['profit'].cumsum()

                fig = px.line(
                    history_df_sorted,
                    x='time',
                    y='cumulative_profit',
                    title='Cumulative P&L Over Time',
                    labels={'cumulative_profit': 'Cumulative P&L ($)', 'time': 'Date'}
                )

                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                # Detailed history table
                display_cols = ['ticket', 'symbol', 'type', 'volume', 'price', 
                               'profit', 'commission', 'time']
                history_display = history_df[display_cols].tail(50)

                st.dataframe(history_display, use_container_width=True)

    # Risk warnings
    st.markdown("---")
    st.subheader("⚠️ Risk Warnings")

    warnings = []

    if risk_metrics['drawdown'] > max_drawdown:
        warnings.append(f"🔴 Drawdown exceeds limit: {risk_metrics['drawdown']:.2f}% > {max_drawdown}%")

    if risk_metrics['risk_score'] > 70:
        warnings.append(f"🔴 High risk score: {risk_metrics['risk_score']:.1f}/100")

    if len(positions_df) > max_positions:
        warnings.append(f"🟡 Too many open positions: {len(positions_df)} > {max_positions}")

    if daily_stats['loss_today'] > account_info.get('balance', 0) * daily_loss_limit / 100:
        warnings.append(f"🔴 Daily loss limit approaching: ${daily_stats['loss_today']:.2f}")

    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("✅ All risk parameters within limits")

    # Footer with last update time
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
