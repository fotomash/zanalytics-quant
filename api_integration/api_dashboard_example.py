import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our API data loader
from zanflow_api_data_loader import ZanflowAPIDataLoader

def main():
    """
    Main function to demonstrate API data loading and visualization.
    This can be used as a template for updating your dashboards.
    """
    print("ZANFLOW API Dashboard Example")
    print("============================")

    # Initialize the API data loader
    # You can specify the API URL here or use environment variables
    api_url = os.getenv('DJANGO_API_URL', 'http://django:8000')
    data_loader = ZanflowAPIDataLoader(api_url=api_url)

    # Get available symbols and timeframes
    symbols = data_loader.get_available_symbols()
    timeframes = data_loader.get_available_timeframes()

    print(f"Available symbols: {', '.join(symbols)}")
    print(f"Available timeframes: {', '.join(timeframes)}")

    # Select a symbol and timeframe
    symbol = "XAUUSD"  # Default symbol
    timeframe = "1h"   # Default timeframe

    print(f"\nLoading data for {symbol} {timeframe}...")

    # Load data from API
    df = data_loader.load_latest_data(symbol=symbol, timeframe=timeframe, limit=100)

    if df.empty:
        print("No data available. Please check your API connection.")
        return

    # Display data summary
    print(f"\nData summary for {symbol} {timeframe}:")
    print(f"Time range: {df['time'].min()} to {df['time'].max()}")
    print(f"Number of bars: {len(df)}")

    if 'open' in df.columns and 'close' in df.columns:
        print(f"Price range: {df['low'].min()} to {df['high'].max()}")

    # Example of data processing
    if 'close' in df.columns:
        # Calculate simple moving averages
        df['SMA20'] = df['close'].rolling(window=20).mean()
        df['SMA50'] = df['close'].rolling(window=50).mean()

        # Calculate daily returns
        df['returns'] = df['close'].pct_change() * 100

        print(f"\nAverage daily return: {df['returns'].mean():.2f}%")
        print(f"Return volatility: {df['returns'].std():.2f}%")

    # Load tick data example
    print("\nLoading tick data...")
    tick_df = data_loader.load_tick_data(symbol=symbol, limit=1000)

    if not tick_df.empty:
        print(f"Loaded {len(tick_df)} ticks for {symbol}")
        print(f"Time range: {tick_df['time'].min()} to {tick_df['time'].max()}")

        if 'bid' in tick_df.columns and 'ask' in tick_df.columns:
            print(f"Average spread: {(tick_df['ask'] - tick_df['bid']).mean():.5f}")
    else:
        print("No tick data available.")

    # Load trades example
    print("\nLoading trades...")
    trades_df = data_loader.load_trades(symbol=symbol, limit=10)

    if not trades_df.empty:
        print(f"Loaded {len(trades_df)} trades for {symbol}")

        if 'pnl' in trades_df.columns:
            print(f"Total PnL: {trades_df['pnl'].sum():.2f}")
            print(f"Win rate: {(trades_df['pnl'] > 0).mean() * 100:.2f}%")
    else:
        print("No trade data available.")

    print("\nAPI Dashboard Example completed successfully.")

if __name__ == "__main__":
    main()
