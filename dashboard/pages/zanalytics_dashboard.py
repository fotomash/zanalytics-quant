#!/usr/bin/env python3
"""
ZAnalytics Dashboard - Updated Version
Interactive trading dashboard without external autorefresh dependency
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Dict, List, Any, Optional
import yfinance as yf

# Configure Streamlit
st.set_page_config(
    page_title="ZAnalytics Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px;
    }
    .success {
        color: #00cc00;
    }
    .danger {
        color: #ff0000;
    }
    .warning {
        color: #ff9900;
    }
</style>
""", unsafe_allow_html=True)


class ZAnalyticsDashboard:
    """Main dashboard class"""

    def __init__(self):
        self.data_dir = Path("data")
        self.results_dir = Path("results")
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize Streamlit session state"""
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = "BTC-USD"
        if 'selected_timeframe' not in st.session_state:
            st.session_state.selected_timeframe = "1d"
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False

    def load_market_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Load market data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            st.error(f"Failed to load data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def load_latest_analysis(self, analysis_type: str) -> Optional[Dict]:
        """Load latest analysis results"""
        try:
            pattern = f"{analysis_type}_*.json"
            files = list(self.results_dir.glob(pattern))
            if files:
                latest_file = max(files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            st.error(f"Failed to load {analysis_type}: {str(e)}")
        return None

    def create_price_chart(self, data: pd.DataFrame, symbol: str) -> go.Figure:
        """Create interactive price chart with volume"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{symbol} Price", "Volume")
        )

        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="OHLC"
            ),
            row=1, col=1
        )

        # Volume bars
        colors = ['red' if close < open else 'green' 
                 for close, open in zip(data['Close'], data['Open'])]

        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data['Volume'],
                marker_color=colors,
                name="Volume"
            ),
            row=2, col=1
        )

        # Add moving averages
        if len(data) >= 20:
            ma20 = data['Close'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=ma20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )

        if len(data) >= 50:
            ma50 = data['Close'].rolling(window=50).mean()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=ma50,
                    mode='lines',
                    name='MA50',
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )

        # Update layout
        fig.update_layout(
            title=f"{symbol} Price Chart",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_dark",
            height=600,
            showlegend=True,
            xaxis_rangeslider_visible=False
        )

        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        return fig

    def create_technical_indicators_chart(self, data: pd.DataFrame) -> go.Figure:
        """Create technical indicators chart"""
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=("RSI", "MACD", "Bollinger Bands")
        )

        # Calculate indicators
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        fig.add_trace(
            go.Scatter(x=data.index, y=rsi, name="RSI", line=dict(color='purple')),
            row=1, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=1, col=1)

        # MACD
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()

        fig.add_trace(
            go.Scatter(x=data.index, y=macd, name="MACD", line=dict(color='blue')),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=signal, name="Signal", line=dict(color='red')),
            row=2, col=1
        )

        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        sma = data['Close'].rolling(window=bb_period).mean()
        std = data['Close'].rolling(window=bb_period).std()
        upper_band = sma + (std * bb_std)
        lower_band = sma - (std * bb_std)

        fig.add_trace(
            go.Scatter(x=data.index, y=data['Close'], name="Close", line=dict(color='white')),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=upper_band, name="Upper BB", line=dict(color='red', dash='dash')),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=lower_band, name="Lower BB", line=dict(color='green', dash='dash')),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=data.index, y=sma, name="SMA", line=dict(color='yellow', dash='dot')),
            row=3, col=1
        )

        fig.update_layout(
            title="Technical Indicators",
            template="plotly_dark",
            height=800,
            showlegend=True
        )

        return fig

    def display_metrics(self, data: pd.DataFrame):
        """Display key metrics"""
        if len(data) == 0:
            return

        latest_price = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else latest_price
        price_change = latest_price - prev_close
        price_change_pct = (price_change / prev_close) * 100

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Current Price",
                f"${latest_price:,.2f}",
                f"{price_change:+.2f} ({price_change_pct:+.2f}%)"
            )

        with col2:
            st.metric(
                "24h High",
                f"${data['High'].iloc[-1]:,.2f}"
            )

        with col3:
            st.metric(
                "24h Low",
                f"${data['Low'].iloc[-1]:,.2f}"
            )

        with col4:
            st.metric(
                "Volume",
                f"{data['Volume'].iloc[-1]:,.0f}"
            )

    def display_signals(self):
        """Display trading signals"""
        signals = self.load_latest_analysis("signal_generation")

        if signals and 'signals' in signals:
            st.subheader("📊 Trading Signals")

            for symbol, signal_data in signals['signals'].items():
                if isinstance(signal_data, dict):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        signal = signal_data.get('signal', 'NEUTRAL')
                        color = "success" if signal == "BUY" else "danger" if signal == "SELL" else "warning"
                        st.markdown(f"<h3 class='{color}'>{symbol}: {signal}</h3>", unsafe_allow_html=True)

                    with col2:
                        confidence = signal_data.get('confidence', 0)
                        st.metric("Confidence", f"{confidence:.1%}")

                    with col3:
                        if 'entry_price' in signal_data:
                            st.metric("Entry Price", f"${signal_data['entry_price']:,.2f}")

    def display_risk_metrics(self):
        """Display risk metrics"""
        risk_data = self.load_latest_analysis("risk_assessment")

        if risk_data and 'risk_metrics' in risk_data:
            st.subheader("⚠️ Risk Metrics")

            metrics = risk_data['risk_metrics']
            if st.session_state.selected_symbol.replace('-', '/') in metrics:
                symbol_metrics = metrics[st.session_state.selected_symbol.replace('-', '/')]

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    var = symbol_metrics.get('var_95', 0)
                    st.metric("VaR (95%)", f"{var:.2%}")

                with col2:
                    sharpe = symbol_metrics.get('sharpe_ratio', 0)
                    st.metric("Sharpe Ratio", f"{sharpe:.2f}")

                with col3:
                    volatility = symbol_metrics.get('volatility', 0)
                    st.metric("Volatility", f"{volatility:.2%}")

                with col4:
                    max_dd = symbol_metrics.get('max_drawdown', 0)
                    st.metric("Max Drawdown", f"{max_dd:.2%}")

    def run(self):
        """Run the dashboard"""
        st.title("🚀 ZAnalytics Trading Dashboard")

        # Sidebar
        with st.sidebar:
            st.header("Settings")

            # Symbol selection
            symbols = ["BTC-USD", "ETH-USD", "SPY", "AAPL", "GOOGL"]
            st.session_state.selected_symbol = st.selectbox(
                "Select Symbol",
                symbols,
                index=symbols.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in symbols else 0
            )

            # Timeframe selection
            timeframes = {
                "1d": "1 Day",
                "5d": "5 Days",
                "1mo": "1 Month",
                "3mo": "3 Months",
                "6mo": "6 Months",
                "1y": "1 Year"
            }

            selected_key = st.selectbox(
                "Select Timeframe",
                list(timeframes.keys()),
                format_func=lambda x: timeframes[x],
                index=list(timeframes.keys()).index(st.session_state.selected_timeframe)
            )
            st.session_state.selected_timeframe = selected_key

            # Auto-refresh toggle
            st.session_state.auto_refresh = st.checkbox(
                "Auto Refresh (30s)",
                value=st.session_state.auto_refresh
            )

            # Manual refresh button
            if st.button("🔄 Refresh Now"):
                st.session_state.last_update = datetime.now()
                st.rerun()

            # Display last update time
            st.text(f"Last Update: {st.session_state.last_update.strftime('%H:%M:%S')}")

            # Add some space
            st.markdown("---")

            # System status
            st.subheader("System Status")

            # Check for results files
            if self.results_dir.exists():
                result_files = list(self.results_dir.glob("*.json"))
                st.success(f"✅ {len(result_files)} analysis files found")
            else:
                st.warning("⚠️ No results directory found")

        # Main content
        # Load market data
        data = self.load_market_data(
            st.session_state.selected_symbol,
            st.session_state.selected_timeframe
        )

        if not data.empty:
            # Display metrics
            self.display_metrics(data)

            # Display signals
            self.display_signals()

            # Display risk metrics
            self.display_risk_metrics()

            # Charts
            tab1, tab2, tab3 = st.tabs(["📈 Price Chart", "📊 Technical Indicators", "📉 Analysis"])

            with tab1:
                fig = self.create_price_chart(data, st.session_state.selected_symbol)
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                fig = self.create_technical_indicators_chart(data)
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                # Load and display latest analysis
                analysis = self.load_latest_analysis("comprehensive_analysis")
                if analysis:
                    st.json(analysis)
                else:
                    st.info("No analysis data available yet. Run the orchestrator to generate analysis.")

        else:
            st.error("Failed to load market data")

        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(30)
            st.rerun()


def main():
    """Main entry point"""
    dashboard = ZAnalyticsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
