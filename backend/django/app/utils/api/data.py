import os
import requests
import traceback
from typing import List, Dict
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import logging

from app.utils.constants import MT5Timeframe

load_dotenv()
logger = logging.getLogger(__name__)

# Prefer MT5_URL (bridge in single-container setup), then MT5_API_URL, then default
BASE_URL = os.getenv('MT5_URL') or os.getenv('MT5_API_URL') or 'http://mt5:5001'
DEFAULT_TIMEOUT = float(os.getenv('MT5_HTTP_TIMEOUT', '2.5'))

# Feature flags: disable unsupported endpoints when only bridge is present
FLAGS = {
    'ticks_enabled': str(os.getenv('MT5_TICKS_ENABLED', '0')).lower() not in ('0', 'false', 'no'),
    'bars_enabled': str(os.getenv('MT5_BARS_ENABLED', '0')).lower() not in ('0', 'false', 'no'),
}

def symbol_info_tick(symbol: str) -> pd.DataFrame:
    try:
        url = f"{BASE_URL}/symbol_info_tick/{symbol}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        # Wrap the data in a list to create a single-row DataFrame
        df = pd.DataFrame([data])
        return df
    except Exception as e:
        error_msg = f"Exception fetching symbol info tick for {symbol}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)

def symbol_info(symbol) -> pd.DataFrame:
    try:
        url = f"{BASE_URL}/symbol_info/{symbol}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame([data])
        return df
    except Exception as e:
        error_msg = f"Exception fetching symbol info for {symbol}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)

def fetch_data_pos(symbol: str, timeframe: MT5Timeframe, bars: int) -> pd.DataFrame:
    try:
        url = f"{BASE_URL}/fetch_data_pos?symbol={symbol}&timeframe={timeframe.value}&bars={bars}"
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        error_msg = f"Exception fetching data for {symbol} on {timeframe}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)

def fetch_data_range(symbol: str, timeframe: MT5Timeframe, from_date: datetime, to_date: datetime) -> pd.DataFrame:
    try:
        url = f"{BASE_URL}/copy_rates_range"
        params = {
            'symbol': symbol,
            'timeframe': timeframe.value,
            'from_date': from_date,
            'to_date': to_date
        }
        response = requests.post(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        error_msg = f"Exception fetching data for {symbol} on {timeframe}: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)


def fetch_ticks(symbol: str, limit: int = 100) -> pd.DataFrame:
    """Fetch recent ticks for a symbol"""
    try:
        if not FLAGS['ticks_enabled']:
            logger.info("MT5 ticks disabled by flag; returning empty DataFrame")
            return pd.DataFrame()
        url = f"{BASE_URL}/ticks"
        params = {"symbol": symbol, "limit": limit}
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        df = pd.DataFrame(data)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        logger.error(f"Exception fetching ticks for {symbol}: {e}\n{traceback.format_exc()}")


def fetch_bars(symbol: str, timeframe: MT5Timeframe, limit: int = 100) -> pd.DataFrame:
    """Fetch OHLC bars for a symbol and timeframe"""
    try:
        if not FLAGS['bars_enabled']:
            logger.info("MT5 bars disabled by flag; returning empty DataFrame")
            return pd.DataFrame()
        url = f"{BASE_URL}/bars/{symbol}/{timeframe.value}"
        params = {"limit": limit}
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        df = pd.DataFrame(data)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        logger.error(f"Exception fetching bars for {symbol} {timeframe.value}: {e}\n{traceback.format_exc()}")
