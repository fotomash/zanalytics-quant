#!/usr/bin/env python3
"""
ZANFLOW v12 Ultimate Trading Dashboard - Enhanced with Live Data
Integrates live data from mm20.local API while maintaining original styling
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
import warnings
import requests
import time
from typing import Dict, List, Optional, Tuple, Any
import re
import base64
warnings.filterwarnings('ignore')

# Add this at the top after imports
class LiveDataConnector:
    """Connect to mm20.local API for live data"""

    def __init__(self, api_url="http://mm20.local:8080"):
        self.api_url = api_url
        self._test_connection()

    def _test_connection(self):
        """Test API connection"""
        try:
            response = requests.get(f"{self.api_url}/symbols", timeout=2)
            if response.status_code == 200:
                st.sidebar.success("✅ Connected to mm20.local")
            else:
                st.sidebar.warning("⚠️ API connected but returned error")
        except:
            st.sidebar.error("❌ Cannot connect to mm20.local:8080")

    def get_symbols(self):
        """Get all available symbols"""
        try:
            response = requests.get(f"{self.api_url}/symbols")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def get_live_data(self, symbol):
        """Get live data for a symbol"""
        try:
            response = requests.get(f"{self.api_url}/data/{symbol}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def get_history(self, symbol, limit=100):
        """Get historical data from API"""
        try:
            # This assumes your API has a history endpoint
            response = requests.get(f"{self.api_url}/history/{symbol}?limit={limit}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

# Insert the LiveDataConnector initialization into the existing class
def create_live_price_chart(self, df, pair, timeframe, live_connector):
    """Create ultimate price chart with live data overlay"""

    # Get live data
    live_data = None
    if live_connector:
        live_data = live_connector.get_live_data(pair)

    # Gold header above the chart
    live_badge = ""
    if live_data:
        live_badge = " <span style='color: #00ff00; font-size: 0.8em;'>● LIVE</span>"

    st.markdown(
        f"<div style='text-align:center; font-size:1.12em; color:#ffe082; font-weight:700; margin-bottom:0.2em;'>"
        f"{pair} {timeframe} – Price Action & SMC Overlays{live_badge}"
        f"</div>",
        unsafe_allow_html=True
    )

    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=[
            f"{pair} {timeframe} - Price Action & Smart Money Analysis",
            "Volume Profile",
            "Momentum Oscillators",
            "Market Structure"
        ],
        vertical_spacing=0.05,
        row_heights=[0.5, 0.2, 0.15, 0.15],
        shared_xaxes=True
    )

    # --- Original Candlestick chart ---
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='limegreen',
            decreasing_line_color='crimson',
            increasing_line_width=2.5,
            decreasing_line_width=2.5,
        ), row=1, col=1
    )

    # --- ADD LIVE PRICE MARKER ---
    if live_data:
        current_time = pd.Timestamp.now()
        bid = float(live_data.get('bid', 0))
        ask = float(live_data.get('ask', 0))
        mid_price = (bid + ask) / 2

        # Add live price line
        fig.add_trace(go.Scatter(
            x=[df.index[-50], current_time],  # Extend from recent data
            y=[df['close'].iloc[-1], mid_price],
            mode='lines',
            name='Live Price',
            line=dict(color='yellow', width=3, dash='dot'),
            showlegend=True
        ), row=1, col=1)

        # Add bid/ask markers
        fig.add_trace(go.Scatter(
            x=[current_time],
            y=[bid],
            mode='markers+text',
            name='Bid',
            text=[f"Bid: {bid:.5f}"],
            textposition="bottom center",
            marker=dict(size=12, color='limegreen', symbol='triangle-up'),
            showlegend=True
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=[current_time],
            y=[ask],
            mode='markers+text',
            name='Ask',
            text=[f"Ask: {ask:.5f}"],
            textposition="top center",
            marker=dict(size=12, color='crimson', symbol='triangle-down'),
            showlegend=True
        ), row=1, col=1)

        # Add spread annotation
        spread = float(live_data.get('spread', 0))
        fig.add_annotation(
            x=current_time,
            y=mid_price,
            text=f"Spread: {spread}",
            showarrow=True,
            arrowhead=2,
            ax=40,
            ay=-40,
            bgcolor="rgba(255,255,0,0.8)",
            font=dict(color="black", size=10)
        )

    # --- Rest of original chart code ---
    # Moving averages with labels
    ma_colors = {'ema_8': '#ff6b6b', 'ema_21': '#4ecdc4', 'ema_55': '#45b7d1', 'sma_200': '#96ceb4'}
    for ma, color in ma_colors.items():
        if ma in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[ma],
                mode='lines', name=ma.upper(),
                line=dict(color=color, width=2.7)
            ), row=1, col=1)

    # Bollinger Bands
    if all(col in df.columns for col in ['BB_Upper_20', 'BB_Lower_20']):
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Upper_20'],
            mode='lines', name='BB Upper',
            line=dict(color='rgba(200,200,200,0.7)', width=1.4, dash='dash'),
            showlegend=False
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Lower_20'],
            mode='lines', name='BB Lower',
            line=dict(color='rgba(200,200,200,0.7)', width=1.4, dash='dash'),
            fill='tonexty', fillcolor='rgba(128,128,128,0.10)',
            showlegend=False
        ), row=1, col=1)

    # SMC Analysis overlays
    if st.session_state.get('show_smc', True) and hasattr(self, 'add_smc_overlays'):
        self.add_smc_overlays(fig, df, row=1)

    # Wyckoff Analysis overlays
    if st.session_state.get('show_wyckoff', True) and hasattr(self, 'add_wyckoff_overlays'):
        self.add_wyckoff_overlays(fig, df, row=1)

    # --- ENHANCED VOLUME WITH LIVE DATA ---
    if 'volume' in df.columns:
        colors = ['green' if close >= open_val else 'red'
                 for close, open_val in zip(df['close'], df['open'])]

        fig.add_trace(go.Bar(
            x=df.index, y=df['volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7,
            marker_line_width=1.2,
            marker_line_color='rgba(0,0,0,0.2)'
        ), row=2, col=1)

        # Add live volume if available
        if live_data and 'volume' in live_data:
            vol_data = live_data['volume']
            tick_vol = vol_data.get('tick', 0)

            # Add live volume bar
            fig.add_trace(go.Bar(
                x=[current_time],
                y=[tick_vol],
                name='Live Volume',
                marker_color='yellow',
                opacity=0.9,
                width=60000 * 60,  # 1 minute width in milliseconds
                showlegend=False
            ), row=2, col=1)

        # Volume moving average
        if 'volume_sma_20' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['volume_sma_20'],
                mode='lines', name='Vol MA20',
                line=dict(color='orange', width=2.2)
            ), row=2, col=1)

    # --- LIVE MOMENTUM INDICATORS ---
    if 'rsi_14' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['rsi_14'],
            mode='lines', name='RSI',
            line=dict(color='#9b59b6', width=2.5)
        ), row=3, col=1)

        # Add live RSI if available
        if live_data and 'enriched' in live_data:
            live_rsi = live_data['enriched'].get('rsi', 50)
            fig.add_trace(go.Scatter(
                x=[current_time],
                y=[live_rsi],
                mode='markers+text',
                name='Live RSI',
                text=[f"{live_rsi:.1f}"],
                textposition="top center",
                marker=dict(size=10, color='yellow'),
                showlegend=False
            ), row=3, col=1)

        # RSI levels
        fig.add_hline(y=70, line_color="red", line_width=1, line_dash="dash", row=3, col=1)
        fig.add_hline(y=30, line_color="green", line_width=1, line_dash="dash", row=3, col=1)

    # MACD
    if all(col in df.columns for col in ['macd', 'macd_signal']):
        fig.add_trace(go.Scatter(
            x=df.index, y=df['macd'],
            mode='lines', name='MACD',
            line=dict(color='#3498db', width=2.2)
        ), row=4, col=1)

        fig.add_trace(go.Scatter(
            x=df.index, y=df['macd_signal'],
            mode='lines', name='Signal',
            line=dict(color='#e74c3c', width=2.2)
        ), row=4, col=1)

        if 'macd_histogram' in df.columns:
            colors = ['green' if val > 0 else 'red' for val in df['macd_histogram']]
            fig.add_trace(go.Bar(
                x=df.index, y=df['macd_histogram'],
                name='Histogram',
                marker_color=colors,
                opacity=0.6
            ), row=4, col=1)

    # --- Ultimate Layout Styling (Black Theme) ---
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(color="white", size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.8)",
            bordercolor="gray",
            borderwidth=1
        ),
        margin=dict(l=50, r=50, t=100, b=50),
        height=1000,
        hovermode='x unified'
    )

    # Update all axes
    for i in range(1, 5):
        fig.update_xaxes(
            gridcolor="rgba(128,128,128,0.2)",
            zeroline=False,
            showline=True,
            linecolor="gray",
            linewidth=1,
            row=i, col=1
        )
        fig.update_yaxes(
            gridcolor="rgba(128,128,128,0.2)",
            zeroline=False,
            showline=True,
            linecolor="gray",
            linewidth=1,
            row=i, col=1
        )

    # Add rangeslider only to bottom subplot
    fig.update_xaxes(rangeslider_visible=True, row=4, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Add live data metrics below chart
    if live_data:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Bid", f"{live_data.get('bid', 0):.5f}")
        with col2:
            st.metric("Ask", f"{live_data.get('ask', 0):.5f}")
        with col3:
            st.metric("Spread", f"{live_data.get('spread', 0)}")
        with col4:
            if 'enriched' in live_data:
                trend = live_data['enriched'].get('trend', 'NEUTRAL')
                trend_emoji = {'UPTREND': '📈', 'DOWNTREND': '📉', 'NEUTRAL': '➡️'}
                st.metric("Trend", f"{trend_emoji.get(trend, '')} {trend}")
        with col5:
            if 'volume' in live_data:
                vol_per_min = live_data['volume'].get('per_minute', 0)
                st.metric("Vol/Min", f"{vol_per_min:.1f}")
