import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import logging
from datetime import datetime, timedelta

# Import our API data loader
from zanflow_api_data_loader import ZanflowAPIDataLoader

# Set page config
st.set_page_config(
    page_title="ZANFLOW API Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Title and description
st.title("ZANFLOW API Dashboard")
st.markdown("This dashboard connects directly to the Django API instead of using parquet files.")

# Initialize the API data loader
@st.cache_resource
def get_data_loader():
    # You can specify the API URL here or use environment variables
    api_url = os.getenv('DJANGO_API_URL')
    if api_url is None:
        try:
            api_url = st.secrets.get("DJANGO_API_URL", "http://django:8000")
        except:
            api_url = "http://django:8000"

    return ZanflowAPIDataLoader(api_url=api_url)

data_loader = get_data_loader()

# Sidebar for settings
st.sidebar.header("Settings")

# Get available symbols and timeframes
symbols = data_loader.get_available_symbols()
timeframes = data_loader.get_available_timeframes()

# Symbol and timeframe selection
symbol = st.sidebar.selectbox("Symbol", symbols, index=symbols.index("XAUUSD") if "XAUUSD" in symbols else 0)
timeframe = st.sidebar.selectbox("Timeframe", timeframes, index=timeframes.index("1h") if "1h" in timeframes else 0)
data_limit = st.sidebar.slider("Number of bars", min_value=50, max_value=1000, value=200, step=50)

# Load data button
if st.sidebar.button("Load Data"):
    with st.spinner(f"Loading {symbol} {timeframe} data..."):
        # Load data from API
        df = data_loader.load_latest_data(symbol=symbol, timeframe=timeframe, limit=data_limit)

        if df.empty:
            st.error("No data available. Please check your API connection.")
        else:
            # Display data summary
            st.subheader(f"Data Summary for {symbol} {timeframe}")

            # Create metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Number of Bars", len(df))

            with col2:
                if 'time' in df.columns:
                    time_range = f"{df['time'].min().strftime('%Y-%m-%d')} to {df['time'].max().strftime('%Y-%m-%d')}"
                    st.metric("Time Range", time_range)

            with col3:
                if 'close' in df.columns:
                    latest_price = df['close'].iloc[-1]
                    previous_price = df['close'].iloc[-2]
                    price_change = latest_price - previous_price
                    st.metric("Latest Price", f"{latest_price:.5f}", f"{price_change:.5f}")

            # Create price chart
            if all(col in df.columns for col in ['time', 'open', 'high', 'low', 'close']):
                st.subheader("Price Chart")

                # Calculate indicators
                df['SMA20'] = df['close'].rolling(window=20).mean()
                df['SMA50'] = df['close'].rolling(window=50).mean()

                # Create figure
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                   vertical_spacing=0.03, row_heights=[0.7, 0.3],
                                   subplot_titles=(f"{symbol} {timeframe} Chart", "Volume"))

                # Add candlestick chart
                fig.add_trace(
                    go.Candlestick(
                        x=df['time'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="Price"
                    ),
                    row=1, col=1
                )

                # Add moving averages
                fig.add_trace(
                    go.Scatter(
                        x=df['time'],
                        y=df['SMA20'],
                        name="SMA20",
                        line=dict(color='blue', width=1)
                    ),
                    row=1, col=1
                )

                fig.add_trace(
                    go.Scatter(
                        x=df['time'],
                        y=df['SMA50'],
                        name="SMA50",
                        line=dict(color='red', width=1)
                    ),
                    row=1, col=1
                )

                # Add volume chart if available
                if 'volume' in df.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df['time'],
                            y=df['volume'],
                            name="Volume",
                            marker_color='rgba(0, 0, 255, 0.5)'
                        ),
                        row=2, col=1
                    )

                # Update layout
                fig.update_layout(
                    height=600,
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Display statistics
                st.subheader("Statistics")

                col1, col2 = st.columns(2)

                with col1:
                    df['returns'] = df['close'].pct_change() * 100
                    st.metric("Average Return", f"{df['returns'].mean():.2f}%")
                    st.metric("Return Volatility", f"{df['returns'].std():.2f}%")

                with col2:
                    if 'high' in df.columns and 'low' in df.columns:
                        avg_range = ((df['high'] - df['low']) / df['low'] * 100).mean()
                        st.metric("Average Range", f"{avg_range:.2f}%")

                    if 'SMA20' in df.columns and 'SMA50' in df.columns:
                        trend = "Bullish" if df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1] else "Bearish"
                        st.metric("Trend", trend)

            # Display raw data
            with st.expander("View Raw Data"):
                st.dataframe(df)

# Tick Data Section
st.sidebar.header("Tick Data")
tick_symbol = st.sidebar.selectbox("Tick Symbol", symbols, index=symbols.index("XAUUSD") if "XAUUSD" in symbols else 0, key="tick_symbol")
tick_limit = st.sidebar.slider("Number of ticks", min_value=100, max_value=10000, value=1000, step=100)

if st.sidebar.button("Load Tick Data"):
    with st.spinner(f"Loading {tick_symbol} tick data..."):
        # Load tick data from API
        tick_df = data_loader.load_tick_data(symbol=tick_symbol, limit=tick_limit)

        if tick_df.empty:
            st.error("No tick data available. Please check your API connection.")
        else:
            st.subheader(f"Tick Data for {tick_symbol}")

            # Display tick metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Number of Ticks", len(tick_df))

            with col2:
                if 'time' in tick_df.columns:
                    time_range = f"{tick_df['time'].min().strftime('%Y-%m-%d %H:%M:%S')} to {tick_df['time'].max().strftime('%Y-%m-%d %H:%M:%S')}"
                    st.metric("Time Range", time_range)

            with col3:
                if 'bid' in tick_df.columns and 'ask' in tick_df.columns:
                    avg_spread = (tick_df['ask'] - tick_df['bid']).mean()
                    st.metric("Average Spread", f"{avg_spread:.5f}")

            # Create tick chart
            if all(col in tick_df.columns for col in ['time', 'bid', 'ask']):
                st.subheader("Tick Chart")

                # Create figure
                fig = go.Figure()

                # Add bid line
                fig.add_trace(
                    go.Scatter(
                        x=tick_df['time'],
                        y=tick_df['bid'],
                        name="Bid",
                        line=dict(color='red', width=1)
                    )
                )

                # Add ask line
                fig.add_trace(
                    go.Scatter(
                        x=tick_df['time'],
                        y=tick_df['ask'],
                        name="Ask",
                        line=dict(color='green', width=1)
                    )
                )

                # Update layout
                fig.update_layout(
                    height=400,
                    template="plotly_dark",
                    title=f"{tick_symbol} Bid/Ask Prices"
                )

                st.plotly_chart(fig, use_container_width=True)

            # Display raw tick data
            with st.expander("View Raw Tick Data"):
                st.dataframe(tick_df)

# Trades Section
st.sidebar.header("Trades")
trade_symbol = st.sidebar.selectbox("Trade Symbol", ["All"] + symbols, index=0, key="trade_symbol")
trade_limit = st.sidebar.slider("Number of trades", min_value=10, max_value=100, value=20, step=10)

if st.sidebar.button("Load Trades"):
    with st.spinner(f"Loading trade data..."):
        # Load trade data from API
        symbol_param = None if trade_symbol == "All" else trade_symbol
        trades_df = data_loader.load_trades(symbol=symbol_param, limit=trade_limit)

        if trades_df.empty:
            st.error("No trade data available. Please check your API connection.")
        else:
            st.subheader(f"Trade Data for {trade_symbol}")

            # Display trade metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Number of Trades", len(trades_df))

            with col2:
                if 'pnl' in trades_df.columns:
                    total_pnl = trades_df['pnl'].sum()
                    st.metric("Total PnL", f"{total_pnl:.2f}")

            with col3:
                if 'pnl' in trades_df.columns:
                    win_rate = (trades_df['pnl'] > 0).mean() * 100
                    st.metric("Win Rate", f"{win_rate:.2f}%")

            # Create PnL chart
            if 'pnl' in trades_df.columns and 'entry_time' in trades_df.columns:
                st.subheader("PnL Chart")

                # Sort by entry time
                trades_df = trades_df.sort_values('entry_time')

                # Calculate cumulative PnL
                trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()

                # Create figure
                fig = go.Figure()

                # Add cumulative PnL line
                fig.add_trace(
                    go.Scatter(
                        x=trades_df['entry_time'],
                        y=trades_df['cumulative_pnl'],
                        name="Cumulative PnL",
                        line=dict(color='blue', width=2)
                    )
                )

                # Add individual trade markers
                fig.add_trace(
                    go.Scatter(
                        x=trades_df['entry_time'],
                        y=trades_df['pnl'],
                        mode='markers',
                        name="Individual Trades",
                        marker=dict(
                            size=8,
                            color=trades_df['pnl'],
                            colorscale='RdYlGn',
                            cmin=-max(abs(trades_df['pnl'])),
                            cmax=max(abs(trades_df['pnl']))
                        )
                    )
                )

                # Update layout
                fig.update_layout(
                    height=400,
                    template="plotly_dark",
                    title="Trade Performance"
                )

                st.plotly_chart(fig, use_container_width=True)

            # Display raw trade data
            with st.expander("View Raw Trade Data"):
                st.dataframe(trades_df)

# Footer
st.sidebar.markdown("---")
st.sidebar.info("This dashboard connects to the Django API to fetch data instead of using parquet files.")
