import pandas as pd
from typing import Dict, List, Optional
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache

class ZanflowAPIDataLoader:
    """Data loader for ZANFLOW that uses the Django API instead of parquet files"""

    def __init__(self, api_url=None, token: Optional[str] = None):
        """
        Initialize the data loader with API connection.

        Args:
            api_url: The base URL for the Django API. If None, uses ``DJANGO_API_URL``.
            token: API token. If None, uses ``DJANGO_API_TOKEN``.
        """
        # Import here to avoid dependency issues
        from django_api_client import DjangoAPIClient

        # Get API URL and token from environment if not provided
        self.api_url = api_url or os.getenv('DJANGO_API_URL', "http://django:8000")
        self.token = token or os.getenv('DJANGO_API_TOKEN')

        # Initialize the API client
        self.api_client = DjangoAPIClient(base_url=self.api_url, token=self.token)
        self.logger = logging.getLogger(__name__)

        # Check connection
        if not self.api_client.connected:
            print("⚠️ Could not connect to Django API. Some features may not work.")

    def load_latest_data(self, symbol: str = "XAUUSD", timeframe: str = "5min", limit: int = 1000) -> pd.DataFrame:
        """
        Load the latest data for a symbol/timeframe from the API.

        Args:
            symbol: The symbol to load data for
            timeframe: The timeframe to load data for
            limit: Maximum number of bars to return

        Returns:
            DataFrame containing the data
        """
        try:
            # Get bars from API
            df = self.api_client.get_bars(symbol=symbol, timeframe=timeframe, limit=limit)

            if df.empty:
                self.logger.warning(f"No data returned for {symbol} {timeframe}")
                return pd.DataFrame()

            # Ensure datetime column is properly formatted
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')

            return df
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def load_tick_data(self, symbol: str = "XAUUSD", limit: int = 10000) -> pd.DataFrame:
        """
        Load tick data for a symbol from the API.

        Args:
            symbol: The symbol to load ticks for
            limit: Maximum number of ticks to return

        Returns:
            DataFrame containing tick data
        """
        try:
            # Get ticks from API
            df = self.api_client.get_ticks(symbol=symbol, limit=limit)

            if df.empty:
                self.logger.warning(f"No tick data returned for {symbol}")
                return pd.DataFrame()

            # Ensure datetime column is properly formatted
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')

            return df
        except Exception as e:
            self.logger.error(f"Error loading tick data for {symbol}: {e}")
            return pd.DataFrame()

    def load_trades(self, symbol: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
        """
        Load trades from the API.

        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of trades to return

        Returns:
            DataFrame containing trade data
        """
        try:
            # Get trades from API
            df = self.api_client.get_trades(symbol=symbol, limit=limit)

            if df.empty:
                self.logger.warning(f"No trades returned for {symbol if symbol else 'all symbols'}")
                return pd.DataFrame()

            # Ensure datetime columns are properly formatted
            for col in ['entry_time', 'close_time']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])

            return df
        except Exception as e:
            self.logger.error(f"Error loading trades: {e}")
            return pd.DataFrame()

    @lru_cache(maxsize=1)
    def get_available_symbols(self) -> List[str]:
        """Get a list of available symbols from the API."""
        try:
            symbols = self.api_client.get_symbols()
            return symbols
        except Exception as e:
            self.logger.error(f"Error getting available symbols: {e}")
            return []

    @lru_cache(maxsize=1)
    def get_available_timeframes(self) -> List[str]:
        """Get a list of available timeframes from the API."""
        try:
            timeframes = self.api_client.get_timeframes()
            return timeframes
        except Exception as e:
            self.logger.error(f"Error getting available timeframes: {e}")
            return []
