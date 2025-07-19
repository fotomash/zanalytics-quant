#!/usr/bin/env python3
"""
ZANFLOW Dashboard Integration Helper
Connects your API to existing dashboards
"""

import streamlit as st
import requests
import redis
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import time

# Configuration
API_URL = "http://localhost:8080"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

class ZanflowDataConnector:
    """Connect dashboards to ZANFLOW API"""

    def __init__(self):
        self.api_url = API_URL
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    def get_all_symbols(self):
        """Get all available symbols from API"""
        try:
            response = requests.get(f"{self.api_url}/symbols")
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    def get_symbol_data(self, symbol):
        """Get enriched data for a symbol"""
        try:
            response = requests.get(f"{self.api_url}/data/{symbol}")
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_symbol_history(self, symbol, limit=100):
        """Get historical data from Redis"""
        try:
            history = self.redis.lrange(f"mt5:{symbol}:history", 0, limit-1)
            return [json.loads(h) for h in history]
        except:
            return []

    def subscribe_to_symbol(self, symbol, callback):
        """Subscribe to real-time updates"""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(f"mt5:{symbol}")

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                callback(data)

    def get_account_info(self):
        """Get account information"""
        try:
            info = self.redis.hgetall("account:info")
            return {k: float(v) for k, v in info.items()}
        except:
            return {}

    def create_price_chart(self, symbol_data, history):
        """Create price chart with indicators"""
        df = pd.DataFrame(history)

        fig = go.Figure()

        # Candlestick chart if available
        if 'candles' in symbol_data and symbol_data['candles']:
            candles = symbol_data['candles']
            fig.add_trace(go.Candlestick(
                x=[datetime.fromtimestamp(c['time']) for c in candles],
                open=[c['open'] for c in candles],
                high=[c['high'] for c in candles],
                low=[c['low'] for c in candles],
                close=[c['close'] for c in candles],
                name="Price"
            ))

        # Add bid/ask lines
        fig.add_trace(go.Scatter(
            x=[datetime.now()],
            y=[symbol_data['bid']],
            mode='markers+text',
            name='Bid',
            text=[f"Bid: {symbol_data['bid']}"],
            textposition="top center",
            marker=dict(size=10, color='green')
        ))

        fig.add_trace(go.Scatter(
            x=[datetime.now()],
            y=[symbol_data['ask']],
            mode='markers+text',
            name='Ask',
            text=[f"Ask: {symbol_data['ask']}"],
            textposition="bottom center",
            marker=dict(size=10, color='red')
        ))

        fig.update_layout(
            title=f"{symbol_data['symbol']} Live Chart",
            xaxis_title="Time",
            yaxis_title="Price",
            height=500
        )

        return fig

    def create_volume_chart(self, symbol_data):
        """Create volume analysis chart"""
        volume_data = symbol_data.get('volume', {})

        fig = go.Figure()

        # Volume bars
        fig.add_trace(go.Bar(
            x=['Tick Volume', 'Per Minute', 'Last 5 Min'],
            y=[
                volume_data.get('tick', 0),
                volume_data.get('per_minute', 0),
                volume_data.get('last_5min', 0)
            ],
            text=[
                f"{volume_data.get('tick', 0):.0f}",
                f"{volume_data.get('per_minute', 0):.2f}",
                f"{volume_data.get('last_5min', 0):.2f}"
            ],
            textposition='auto'
        ))

        fig.update_layout(
            title="Volume Analysis",
            yaxis_title="Volume",
            height=300
        )

        return fig

    def create_indicators_chart(self, enriched_data):
        """Create indicators visualization"""
        fig = go.Figure()

        # RSI Gauge
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=enriched_data.get('rsi', 50),
            title={'text': "RSI"},
            domain={'x': [0, 0.3], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 30], 'color': "lightgreen"},
                    {'range': [30, 70], 'color': "lightyellow"},
                    {'range': [70, 100], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ))

        # Momentum
        momentum = enriched_data.get('momentum', 0)
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=momentum,
            title={'text': "Momentum %"},
            delta={'reference': 0},
            domain={'x': [0.35, 0.65], 'y': [0, 1]}
        ))

        # Volatility
        fig.add_trace(go.Indicator(
            mode="number",
            value=enriched_data.get('volatility_1min', 0) * 10000,  # Convert to pips
            title={'text': "Volatility (pips/min)"},
            domain={'x': [0.7, 1], 'y': [0, 1]}
        ))

        fig.update_layout(height=200)
        return fig

# Integration functions for existing dashboards
def integrate_home_dashboard(connector):
    """Integration for home.py dashboard"""
    st.title("🏠 ZANFLOW Trading Dashboard")

    # Account info
    account = connector.get_account_info()
    if account:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Balance", f"${account.get('balance', 0):,.2f}")
        col2.metric("Equity", f"${account.get('equity', 0):,.2f}")
        col3.metric("Margin", f"${account.get('margin', 0):,.2f}")
        col4.metric("Free Margin", f"${account.get('free_margin', 0):,.2f}")

    # Symbol selector
    symbols = connector.get_all_symbols()
    if symbols:
        selected_symbol = st.selectbox("Select Symbol", symbols)

        # Get data
        data = connector.get_symbol_data(selected_symbol)
        if data:
            # Price info
            col1, col2, col3 = st.columns(3)
            col1.metric("Bid", data['bid'])
            col2.metric("Ask", data['ask'])
            col3.metric("Spread", data['spread'])

            # Charts
            history = connector.get_symbol_history(selected_symbol)

            # Price chart
            st.plotly_chart(connector.create_price_chart(data, history), use_container_width=True)

            # Volume chart
            st.plotly_chart(connector.create_volume_chart(data), use_container_width=True)

            # Indicators
            if 'enriched' in data:
                st.plotly_chart(connector.create_indicators_chart(data['enriched']), use_container_width=True)

                # Trend signal
                trend = data['enriched'].get('trend', 'NEUTRAL')
                trend_color = {'UPTREND': '🟢', 'DOWNTREND': '🔴', 'NEUTRAL': '🟡'}
                st.write(f"**Trend:** {trend_color.get(trend, '')} {trend}")

def integrate_strategy_dashboard(connector):
    """Integration for strategy monitoring"""
    st.title("📈 Strategy Monitor")

    # Multi-symbol monitoring
    symbols = connector.get_all_symbols()

    # Create grid of symbols
    cols = st.columns(3)

    for i, symbol in enumerate(symbols):
        with cols[i % 3]:
            data = connector.get_symbol_data(symbol)
            if data:
                with st.container():
                    st.subheader(symbol)

                    # Price
                    mid_price = (data['bid'] + data['ask']) / 2
                    st.metric("Price", f"{mid_price:.5f}")

                    # Enriched data
                    if 'enriched' in data:
                        enriched = data['enriched']

                        # Mini indicators
                        col1, col2 = st.columns(2)
                        col1.metric("RSI", f"{enriched.get('rsi', 50):.1f}")
                        col2.metric("Mom%", f"{enriched.get('momentum', 0):.2f}")

                        # Trend badge
                        trend = enriched.get('trend', 'NEUTRAL')
                        if trend == 'UPTREND':
                            st.success(f"↑ {trend}")
                        elif trend == 'DOWNTREND':
                            st.error(f"↓ {trend}")
                        else:
                            st.info(f"→ {trend}")
