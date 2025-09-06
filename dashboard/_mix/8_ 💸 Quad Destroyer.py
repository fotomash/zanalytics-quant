#!/usr/bin/env python3
def price_fmt(val, symbol):
    """Return price formatted for symbol: 5dp for forex, 2dp for XAUUSD."""
    if symbol.upper() == "XAUUSD":
        return f"{val:,.2f}"
    return f"{val:,.5f}"
"""
ZANFLOW v12 - Institutional Grade Visual Trading Dashboard
Advanced SMC • Midas Model • London Killzone • Wyckoff Analysis
Ultra-Visual Professional Trading Interface
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta, time
import pytz
import warnings
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
from pathlib import Path
import math
# st.set_page_config(
#     page_title="🏛️ Dashboard",
#     page_icon="🏛️",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# --- Add background image as base64 and style ---
import base64
def get_image_as_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        # Only warn after config is set
        return None

img_base64 = get_image_as_base64("theme/image_af247b.jpg")
if img_base64:
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url(data:image/jpeg;base64,{img_base64}) !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
        background-color: transparent !important;
    }}
    body, .block-container {{
        background: none !important;
        background-color: transparent !important;
    }}
    </style>
    """, unsafe_allow_html=True)
elif img_base64 is None:
    st.warning(f"Background image not found at 'theme/image_af247b.jpg'")

# === DYNAMIC PARQUET LOADING FOR MULTI-SYMBOL SUPPORT ===
PARQUET_DATA_DIR = Path(st.secrets.get("PARQUET_DATA_DIR", "/Users/tom/Documents/_trade/_exports/_tick/out/parquet"))
def load_available_parquet_files(parquet_dir):
    symbol_timeframes = []
    for symbol_folder in parquet_dir.glob("*"):
        if symbol_folder.is_dir():
            for file in symbol_folder.glob("*.parquet"):
                try:
                    symbol, tf = file.stem.split("_")
                    symbol_timeframes.append((symbol, tf, file))
                except ValueError:
                    continue
    return symbol_timeframes

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_institutional_page():
    """Setup institutional-grade page configuration (styling only)"""
    # Ultra-Professional Institutional Styling
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .main {
            background: linear-gradient(135deg, #0a0f1c 0%, #1a1f2e 25%, #2d1810 50%, #1a1f2e 75%, #0a0f1c 100%);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }
        
        .institutional-header {
            background: linear-gradient(135deg, #2c5530 0%, #ffd700 25%, #ff8c00 50%, #ffd700 75%, #2c5530 100%);
            padding: 2.5rem;
            border-radius: 25px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 15px 50px rgba(255, 215, 0, 0.4);
            border: 3px solid rgba(255, 215, 0, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .institutional-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                rgba(255, 255, 255, 0.1) 10px,
                rgba(255, 255, 255, 0.1) 20px
            );
            animation: shimmer 3s linear infinite;
            z-index: 1;
        }
        
        .institutional-header h1, .institutional-header h2, .institutional-header p {
            position: relative;
            z-index: 2;
            color: #000;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        @keyframes shimmer {
            0% { transform: translate(-50%, -50%) rotate(0deg); }
            100% { transform: translate(-50%, -50%) rotate(360deg); }
        }
        
        .strategy-card {
            background: linear-gradient(145deg, #1a1f2e, #2a2f3e);
            border: 2px solid #ffd700;
            border-radius: 20px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        .strategy-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 215, 0, 0.2), transparent);
            transition: left 0.7s;
        }
        
        .strategy-card:hover::before {
            left: 100%;
        }
        
        .midas-signal {
            background: linear-gradient(45deg, #ffd700, #ffed4e, #ffc107);
            color: #000;
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.5);
            animation: midas-pulse 2s infinite;
            border: 3px solid #ff8c00;
        }
        
        @keyframes midas-pulse {
            0%, 100% { 
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.5);
                transform: scale(1);
            }
            50% { 
                box-shadow: 0 12px 40px rgba(255, 215, 0, 0.8);
                transform: scale(1.02);
            }
        }
        
        .london-killzone {
            background: linear-gradient(45deg, #ff6b6b, #ee5a52, #dc3545);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.5);
            animation: london-pulse 2s infinite;
            border: 3px solid #dc3545;
        }
        
        @keyframes london-pulse {
            0%, 100% { 
                box-shadow: 0 8px 25px rgba(255, 107, 107, 0.5);
            }
            50% { 
                box-shadow: 0 12px 40px rgba(255, 107, 107, 0.8);
            }
        }
        
        .wyckoff-phase {
            display: inline-block;
            padding: 0.8rem 1.5rem;
            border-radius: 25px;
            font-weight: 600;
            margin: 0.3rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .accumulation { 
            background: linear-gradient(45deg, #28a745, #20c997); 
            color: white; 
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
        }
        .markup { 
            background: linear-gradient(45deg, #007bff, #17a2b8); 
            color: white; 
            box-shadow: 0 4px 15px rgba(0, 123, 255, 0.4);
        }
        .distribution { 
            background: linear-gradient(45deg, #ffc107, #fd7e14); 
            color: #000; 
            box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4);
        }
        .markdown { 
            background: linear-gradient(45deg, #dc3545, #6f42c1); 
            color: white; 
            box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4);
        }
        
        .smc-indicator {
            background: rgba(255, 255, 255, 0.1);
            border: 2px solid;
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            backdrop-filter: blur(10px);
        }
        
        .fvg-bullish { border-color: #28a745; }
        .fvg-bearish { border-color: #dc3545; }
        .order-block { border-color: #6f42c1; }
        .liquidity-zone { border-color: #17a2b8; }
        
        .metric-institutional {
            background: linear-gradient(145deg, #2a2f3e, #3a3f4e);
            padding: 2rem;
            border-radius: 20px;
            border: 2px solid rgba(255, 215, 0, 0.3);
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            position: relative;
        }
        
        .price-display-institutional {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(45deg, #ffd700, #ff8c00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
            margin-bottom: 0.5rem;
        }
        
        .signal-strength-meter {
            width: 100%;
            height: 20px;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
            border-radius: 10px;
            position: relative;
            margin: 1rem 0;
        }
        
        .signal-indicator {
            height: 100%;
            border-radius: 10px;
            background: white;
            position: absolute;
            width: 4px;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }
        
        .session-timeline {
            background: linear-gradient(90deg, #1a1f2e 0%, #2a2f3e 25%, #3a3f4e 50%, #2a2f3e 75%, #1a1f2e 100%);
            border: 2px solid rgba(255, 215, 0, 0.3);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        
        .chart-container-pro {
            background: rgba(0, 0, 0, 0.3);
            border: 2px solid rgba(255, 215, 0, 0.2);
            border-radius: 20px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
        }
        
        .stButton > button {
            background: linear-gradient(45deg, #2c5530, #ffd700);
            color: #000;
            border: none;
            border-radius: 12px;
            padding: 0.8rem 2rem;
            font-weight: 700;
            font-size: 1.1rem;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            background: linear-gradient(45deg, #ffd700, #2c5530);
        }
        
        .alert-high { 
            background: linear-gradient(45deg, #dc3545, #ff6b6b);
            animation: alert-pulse 1s infinite;
        }
        .alert-medium { 
            background: linear-gradient(45deg, #ffc107, #ffed4e);
            color: #000;
        }
        .alert-low { 
            background: linear-gradient(45deg, #28a745, #20c997);
        }
        
        @keyframes alert-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .sidebar .stSelectbox > div > div {
            background: rgba(255, 215, 0, 0.1);
            border: 1px solid rgba(255, 215, 0, 0.3);
        }
        
        .zabar-log {
            background: linear-gradient(145deg, #0a0f1c, #1a1f2e);
            border: 1px solid rgba(255, 215, 0, 0.2);
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# ZANFLOW v12 STRATEGY ENGINES
# ============================================================================

class MidasModelDetector:
    """Advanced Midas Model Detection Engine for Gold"""

    def __init__(self):
        self.ny_tz = pytz.timezone('America/New_York')
        self.signals = []

    def detect_midas_setups(self, df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
        """Detect Midas Model setups with advanced validation"""
        df = df.copy()

        # Initialize Midas columns
        df['midas_window'] = 0
        df['midas_signal'] = False
        df['midas_entry'] = np.nan
        df['midas_stop'] = np.nan
        df['midas_target'] = np.nan
        df['midas_setup_type'] = ''
        df['judas_swing'] = False
        df['displacement_confirmed'] = False

        # Convert to NY timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        df_ny = df.tz_convert(self.ny_tz)

        # Calculate ATR for displacement validation
        try:
            import talib
            atr14 = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=atr_period)
        except:
            atr14 = (df['high'].rolling(atr_period).max() - df['low'].rolling(atr_period).min()).values

        for i in range(len(df_ny)):
            ts = df_ny.index[i]

            # Check for 8PM or 9PM NY time windows
            if ts.minute == 0 and ts.second == 0:
                if ts.hour == 20:  # 8PM NY
                    df.loc[df.index[i], 'midas_window'] = 1
                    self._process_midas_window(df, df_ny, i, atr14, window_type="8PM")
                elif ts.hour == 21:  # 9PM NY
                    df.loc[df.index[i], 'midas_window'] = 2
                    self._process_midas_window(df, df_ny, i, atr14, window_type="9PM")

        return df

    def _process_midas_window(self, df: pd.DataFrame, df_ny: pd.DataFrame, i: int, atr14: np.ndarray, window_type: str):
        """Process individual Midas window for signal detection"""
        # Look back 15 minutes for recent high/low (Asian liquidity)
        lookback_start = max(0, i - 15)
        lookback = df_ny.iloc[lookback_start:i+1]

        if len(lookback) < 5:
            return

        recent_high = lookback['high'].max()
        recent_low = lookback['low'].min()

        # Look forward up to 5 bars for liquidity sweep
        for j in range(i, min(i + 5, len(df_ny))):
            sweep_detected = False
            sweep_direction = None

            # Check for bullish sweep (sweep low, expect bullish reversal)
            if df_ny['low'].iloc[j] < recent_low:
                sweep_detected = True
                sweep_direction = 'bullish'
                df.loc[df.index[j], 'judas_swing'] = True

            # Check for bearish sweep (sweep high, expect bearish reversal)
            elif df_ny['high'].iloc[j] > recent_high:
                sweep_detected = True
                sweep_direction = 'bearish'
                df.loc[df.index[j], 'judas_swing'] = True

            if sweep_detected:
                # Validate displacement with ATR
                if j > 0 and not np.isnan(atr14[j]):
                    displacement = abs(df_ny['close'].iloc[j] - df_ny['close'].iloc[j-1])

                    if displacement >= atr14[j]:
                        df.loc[df.index[j], 'displacement_confirmed'] = True

                        # Generate signal
                        entry_price = df_ny['close'].iloc[j]

                        if sweep_direction == 'bullish':
                            stop_price = recent_low
                            target_price = entry_price + 2 * (entry_price - stop_price)
                        else:
                            stop_price = recent_high
                            target_price = entry_price - 2 * (stop_price - entry_price)

                        df.loc[df.index[j], 'midas_signal'] = True
                        df.loc[df.index[j], 'midas_entry'] = entry_price
                        df.loc[df.index[j], 'midas_stop'] = stop_price
                        df.loc[df.index[j], 'midas_target'] = target_price
                        df.loc[df.index[j], 'midas_setup_type'] = f"{window_type}_{sweep_direction}"

                        self.signals.append({
                            'timestamp': df.index[j],
                            'window': window_type,
                            'direction': sweep_direction,
                            'entry': entry_price,
                            'stop': stop_price,
                            'target': target_price,
                            'rr_ratio': 2.0
                        })

                        break

class LondonKillzoneAnalyzer:
    """London Killzone Trading Strategy Analysis"""

    def __init__(self):
        self.london_start = time(7, 0)  # 7 AM UTC
        self.london_end = time(16, 0)   # 4 PM UTC
        self.signals = []

    def analyze_london_session(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze London session for killzone opportunities"""
        df = df.copy()

        # Add London session identification
        df['is_london_session'] = False
        df['is_london_killzone'] = False
        df['asian_liquidity_high'] = np.nan
        df['asian_liquidity_low'] = np.nan
        df['london_sweep'] = False
        df['london_reversal'] = False

        # Convert to UTC for session analysis
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        elif df.index.tz != pytz.UTC:
            df = df.tz_convert('UTC')

        # Identify London sessions and Asian liquidity
        current_asian_high = None
        current_asian_low = None

        for i in range(len(df)):
            current_time = df.index[i].time()

            # Identify Asian session end and liquidity levels
            if current_time == time(7, 0):  # London open
                if current_asian_high is not None and current_asian_low is not None:
                    df.loc[df.index[i], 'asian_liquidity_high'] = current_asian_high
                    df.loc[df.index[i], 'asian_liquidity_low'] = current_asian_low

            # Track Asian session highs/lows (22:00 UTC to 07:00 UTC)
            if time(22, 0) <= current_time or current_time <= time(7, 0):
                if current_asian_high is None or df['high'].iloc[i] > current_asian_high:
                    current_asian_high = df['high'].iloc[i]
                if current_asian_low is None or df['low'].iloc[i] < current_asian_low:
                    current_asian_low = df['low'].iloc[i]

            # Reset Asian levels at session start
            if current_time == time(22, 0):
                current_asian_high = df['high'].iloc[i]
                current_asian_low = df['low'].iloc[i]

            # London session identification
            if self.london_start <= current_time <= self.london_end:
                df.loc[df.index[i], 'is_london_session'] = True

                # London killzone (first 2 hours: 7-9 AM UTC)
                if time(7, 0) <= current_time <= time(9, 0):
                    df.loc[df.index[i], 'is_london_killzone'] = True

        return self._detect_london_signals(df)

    def _detect_london_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect London killzone trading signals"""
        killzone_data = df[df['is_london_killzone'] == True]

        for i in range(len(df)):
            if not df['is_london_killzone'].iloc[i]:
                continue

            asian_high = df['asian_liquidity_high'].iloc[i]
            asian_low = df['asian_liquidity_low'].iloc[i]

            if pd.isna(asian_high) or pd.isna(asian_low):
                continue

            # Check for liquidity sweeps
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Sweep above Asian high (potential bearish reversal)
            if current_high > asian_high:
                df.loc[df.index[i], 'london_sweep'] = True

                # Look for reversal in next few candles
                for j in range(i+1, min(i+5, len(df))):
                    if df['close'].iloc[j] < asian_high:  # Price back below swept level
                        df.loc[df.index[j], 'london_reversal'] = True
                        break

            # Sweep below Asian low (potential bullish reversal)
            elif current_low < asian_low:
                df.loc[df.index[i], 'london_sweep'] = True

                # Look for reversal in next few candles
                for j in range(i+1, min(i+5, len(df))):
                    if df['close'].iloc[j] > asian_low:  # Price back above swept level
                        df.loc[df.index[j], 'london_reversal'] = True
                        break

        return df

class SMCAnalyzer:
    """Smart Money Concepts Analysis Engine"""

    def __init__(self):
        self.fair_value_gaps = []
        self.order_blocks = []
        self.liquidity_zones = []

    def analyze_smc_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Comprehensive SMC analysis"""
        df = df.copy()

        # Initialize SMC columns
        df['fvg_bullish'] = False
        df['fvg_bearish'] = False
        df['order_block_bullish'] = False
        df['order_block_bearish'] = False
        df['liquidity_sweep'] = False
        df['choch'] = False  # Change of Character
        df['bos'] = False    # Break of Structure

        # Detect Fair Value Gaps
        df = self._detect_fair_value_gaps(df)

        # Detect Order Blocks
        df = self._detect_order_blocks(df)

        # Detect Market Structure Changes
        df = self._detect_market_structure(df)

        # Detect Liquidity Zones
        df = self._detect_liquidity_zones(df)

        return df

    def _detect_fair_value_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect Fair Value Gaps with high precision"""
        for i in range(2, len(df)):
            # Bullish FVG: gap between current low and 2 bars ago high
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                if gap_size > 0.001 * df['close'].iloc[i]:  # Minimum gap threshold
                    df.loc[df.index[i], 'fvg_bullish'] = True
                    self.fair_value_gaps.append({
                        'timestamp': df.index[i],
                        'type': 'bullish',
                        'top': df['low'].iloc[i],
                        'bottom': df['high'].iloc[i-2],
                        'size': gap_size
                    })

            # Bearish FVG: gap between current high and 2 bars ago low
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                if gap_size > 0.001 * df['close'].iloc[i]:  # Minimum gap threshold
                    df.loc[df.index[i], 'fvg_bearish'] = True
                    self.fair_value_gaps.append({
                        'timestamp': df.index[i],
                        'type': 'bearish',
                        'top': df['low'].iloc[i-2],
                        'bottom': df['high'].iloc[i],
                        'size': gap_size
                    })

        return df

    def _detect_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect institutional order blocks"""
        swing_high_period = 10
        swing_low_period = 10

        for i in range(swing_high_period, len(df) - swing_high_period):
            # Bullish Order Block: Last down candle before strong bullish move
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # Down candle
                df['close'].iloc[i+1] > df['open'].iloc[i+1] and  # Next candle up
                df['close'].iloc[i+1] > df['high'].iloc[i]):  # Strong move up

                df.loc[df.index[i], 'order_block_bullish'] = True
                self.order_blocks.append({
                    'timestamp': df.index[i],
                    'type': 'bullish',
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i]
                })

            # Bearish Order Block: Last up candle before strong bearish move
            elif (df['close'].iloc[i] > df['open'].iloc[i] and  # Up candle
                  df['close'].iloc[i+1] < df['open'].iloc[i+1] and  # Next candle down
                  df['close'].iloc[i+1] < df['low'].iloc[i]):  # Strong move down

                df.loc[df.index[i], 'order_block_bearish'] = True
                self.order_blocks.append({
                    'timestamp': df.index[i],
                    'type': 'bearish',
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i]
                })

        return df

    def _detect_market_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect Change of Character and Break of Structure"""
        swing_period = 20

        for i in range(swing_period, len(df) - swing_period):
            # Find recent swing high and low
            recent_high = df['high'].iloc[i-swing_period:i].max()
            recent_low = df['low'].iloc[i-swing_period:i].min()

            # Break of Structure (BOS) - continuation pattern
            if df['close'].iloc[i] > recent_high:  # Bullish BOS
                df.loc[df.index[i], 'bos'] = True
            elif df['close'].iloc[i] < recent_low:  # Bearish BOS
                df.loc[df.index[i], 'bos'] = True

            # Change of Character (CHoCH) - reversal pattern
            # Look for price action that breaks previous structure in opposite direction
            if i > swing_period * 2:
                older_high = df['high'].iloc[i-swing_period*2:i-swing_period].max()
                older_low = df['low'].iloc[i-swing_period*2:i-swing_period].min()

                # CHoCH conditions (simplified)
                if (df['close'].iloc[i] < older_low and
                    df['close'].iloc[i-1] > older_low):  # Bearish CHoCH
                    df.loc[df.index[i], 'choch'] = True
                elif (df['close'].iloc[i] > older_high and
                      df['close'].iloc[i-1] < older_high):  # Bullish CHoCH
                    df.loc[df.index[i], 'choch'] = True

        return df

    def _detect_liquidity_zones(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect areas of accumulated liquidity"""
        volume_threshold = df['volume'].quantile(0.8) if 'volume' in df.columns else None

        for i in range(20, len(df)):
            # High volume at resistance/support levels indicates liquidity
            if volume_threshold and df['volume'].iloc[i] > volume_threshold:
                # Check if price is at a significant level
                recent_range = df.iloc[i-20:i]
                if (df['high'].iloc[i] == recent_range['high'].max() or
                    df['low'].iloc[i] == recent_range['low'].min()):

                    df.loc[df.index[i], 'liquidity_sweep'] = True
                    self.liquidity_zones.append({
                        'timestamp': df.index[i],
                        'price': df['close'].iloc[i],
                        'volume': df['volume'].iloc[i] if 'volume' in df.columns else 0
                    })

        return df

class WyckoffAnalyzer:
    """Advanced Wyckoff Method Analysis"""

    def __init__(self):
        self.phases = []
        self.events = []

    def analyze_wyckoff_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Comprehensive Wyckoff phase and event analysis"""
        df = df.copy()

        # Initialize Wyckoff columns
        df['wyckoff_phase'] = 'Unknown'
        df['wyckoff_event'] = ''
        df['accumulation'] = False
        df['distribution'] = False
        df['markup'] = False
        df['markdown'] = False

        # Calculate necessary indicators for Wyckoff analysis
        df['volume_ma'] = df['volume'].rolling(20).mean() if 'volume' in df.columns else 0
        df['price_volatility'] = df['close'].rolling(20).std()
        df['price_trend'] = df['close'].rolling(50).mean()

        # Detect Wyckoff phases
        df = self._detect_wyckoff_phases(df)

        # Detect Wyckoff events
        df = self._detect_wyckoff_events(df)

        return df

    def _detect_wyckoff_phases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect Wyckoff market phases"""
        for i in range(50, len(df)):
            window = df.iloc[i-20:i+1]

            # Calculate phase characteristics
            avg_volume = window['volume_ma'].mean() if 'volume' in df.columns else 1
            price_range = window['high'].max() - window['low'].min()
            trend_strength = abs(window['close'].iloc[-1] - window['close'].iloc[0]) / price_range

            # Accumulation: High volume, low volatility, sideways price
            if ('volume' in df.columns and
                window['volume'].mean() > avg_volume * 1.2 and
                window['price_volatility'].mean() < df['price_volatility'].quantile(0.3) and
                trend_strength < 0.3):

                df.loc[df.index[i], 'wyckoff_phase'] = 'Accumulation'
                df.loc[df.index[i], 'accumulation'] = True

            # Distribution: High volume, high volatility, topping action
            elif ('volume' in df.columns and
                  window['volume'].mean() > avg_volume * 1.2 and
                  window['price_volatility'].mean() > df['price_volatility'].quantile(0.7) and
                  window['close'].iloc[-1] < window['high'].max() * 0.95):

                df.loc[df.index[i], 'wyckoff_phase'] = 'Distribution'
                df.loc[df.index[i], 'distribution'] = True

            # Markup: Rising prices with good volume
            elif ('volume' in df.columns and
                  window['close'].iloc[-1] > window['close'].iloc[0] * 1.02 and
                  window['volume'].mean() > avg_volume):

                df.loc[df.index[i], 'wyckoff_phase'] = 'Markup'
                df.loc[df.index[i], 'markup'] = True

            # Markdown: Falling prices with volume
            elif ('volume' in df.columns and
                  window['close'].iloc[-1] < window['close'].iloc[0] * 0.98 and
                  window['volume'].mean() > avg_volume):

                df.loc[df.index[i], 'wyckoff_phase'] = 'Markdown'
                df.loc[df.index[i], 'markdown'] = True

        return df

    def _detect_wyckoff_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect specific Wyckoff events"""
        for i in range(20, len(df)):
            if 'volume' not in df.columns:
                continue

            # Selling Climax (SC): High volume, strong down move
            if (df['volume'].iloc[i] > df['volume_ma'].iloc[i] * 2 and
                df['close'].iloc[i] < df['close'].iloc[i-1] and
                (df['close'].iloc[i] - df['low'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) < 0.3):

                df.loc[df.index[i], 'wyckoff_event'] = 'SC'

            # Buying Climax (BC): High volume, strong up move with weak close
            elif (df['volume'].iloc[i] > df['volume_ma'].iloc[i] * 2 and
                  df['close'].iloc[i] > df['close'].iloc[i-1] and
                  (df['close'].iloc[i] - df['low'].iloc[i]) / (df['high'].iloc[i] - df['low'].iloc[i]) > 0.7):

                df.loc[df.index[i], 'wyckoff_event'] = 'BC'

            # Spring: Test of support with lower volume
            elif (df['low'].iloc[i] < df['low'].iloc[i-10:i].min() and
                  df['volume'].iloc[i] < df['volume_ma'].iloc[i] and
                  df['close'].iloc[i] > df['low'].iloc[i]):

                df.loc[df.index[i], 'wyckoff_event'] = 'Spring'

        return df

# ============================================================================
# ADVANCED VISUALIZATION FUNCTIONS
# ============================================================================

def create_institutional_master_chart(df: pd.DataFrame, symbol: str, timeframe: str,
                                     midas_signals: List, smc_data: Dict, wyckoff_data: Dict) -> go.Figure:
    """Create ultra-professional institutional trading chart"""

    # Create comprehensive subplot structure
    fig = make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.01,
        subplot_titles=(
            'Volume Profile & Session Analysis',
            'Smart Money Concepts (SMC)',
            'Wyckoff Phase Analysis',
            'Technical Momentum',
            'ZBAR Signal Matrix'
        ),
        row_heights=[0.35, 0.15, 0.15, 0.15, 0.1, 0.1]
    )

    # Main price chart with institutional styling
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f'{symbol} Price',
            increasing_line_color='#2c5530',
            decreasing_line_color='#8B0000',
            increasing_fillcolor='rgba(44, 85, 48, 0.8)',
            decreasing_fillcolor='rgba(139, 0, 0, 0.8)',
            line=dict(width=2)
        ),
        row=1, col=1
    )

    # Add EMAs with institutional colors
    if 'EMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['EMA_20'],
                mode='lines', name='EMA 20',
                line=dict(color='#FFD700', width=3, dash='solid'),
                opacity=0.9
            ),
            row=1, col=1
        )

    if 'EMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['EMA_50'],
                mode='lines', name='EMA 50',
                line=dict(color='#FF8C00', width=3, dash='dot'),
                opacity=0.9
            ),
            row=1, col=1
        )

    # Add Midas signals with professional markers
    if 'midas_signal' in df.columns:
        midas_data = df[df['midas_signal'] == True]
        if not midas_data.empty:
            price_decimals = ".2f" if symbol.upper() == "XAUUSD" else ".5f"
            for idx in midas_data.index:
                setup_type = df.loc[idx, 'midas_setup_type']
                color = '#FFD700' if 'bullish' in setup_type else '#DC143C'
                fig.add_trace(
                    go.Scatter(
                        x=[idx],
                        y=[df.loc[idx, 'close']],
                        mode='markers',
                        marker=dict(
                            symbol='star-diamond',
                            size=20,
                            color=color,
                            line=dict(color='white', width=3)
                        ),
                        name=f'Midas {setup_type}',
                        hovertemplate=(
                            f'<b>MIDAS SIGNAL</b><br>'
                            f'Type: {setup_type}<br>'
                            f'Entry: $%{{y:{price_decimals}}}<br>'
                            f'Stop: $%{{customdata[0]:{price_decimals}}}<br>'
                            f'Target: $%{{customdata[1]:{price_decimals}}}<br>'
                            f'Time: {idx}<extra></extra>'
                        ),
                        customdata=[[df.loc[idx, "midas_stop"], df.loc[idx, "midas_target"]]],
                        showlegend=False
                    ),
                    row=1, col=1
                )

    # Add London Killzone highlights
    if 'is_london_killzone' in df.columns:
        london_periods = df[df['is_london_killzone'] == True]
        for idx in london_periods.index:
            fig.add_vrect(
                x0=idx, x1=idx + timedelta(hours=1),
                fillcolor="rgba(255, 107, 107, 0.2)",
                layer="below", line_width=0,
                row=1, col=1
            )

    # Add SMC elements
    if 'fvg_bullish' in df.columns:
        fvg_bull = df[df['fvg_bullish'] == True]
        if not fvg_bull.empty:
            price_decimals = ".2f" if symbol.upper() == "XAUUSD" else ".5f"
            fig.add_trace(
                go.Scatter(
                    x=fvg_bull.index,
                    y=fvg_bull['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=12, color='#28a745'),
                    name='Bullish FVG',
                    hovertemplate=f'<b>Bullish Fair Value Gap</b><br>Price: $%{{y:{price_decimals}}}<extra></extra>'
                ),
                row=1, col=1
            )

    if 'fvg_bearish' in df.columns:
        fvg_bear = df[df['fvg_bearish'] == True]
        if not fvg_bear.empty:
            price_decimals = ".2f" if symbol.upper() == "XAUUSD" else ".5f"
            fig.add_trace(
                go.Scatter(
                    x=fvg_bear.index,
                    y=fvg_bear['close'],
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=12, color='#dc3545'),
                    name='Bearish FVG',
                    hovertemplate=f'<b>Bearish Fair Value Gap</b><br>Price: $%{{y:{price_decimals}}}<extra></extra>'
                ),
                row=1, col=1
            )

    # Volume analysis with session coloring
    if 'volume' in df.columns:
        # Color volume bars by session
        volume_colors = []
        for idx in df.index:
            if 'is_london_killzone' in df.columns and df.loc[idx, 'is_london_killzone']:
                volume_colors.append('#ff6b6b')  # London red
            elif 'is_london_session' in df.columns and df.loc[idx, 'is_london_session']:
                volume_colors.append('#ffa500')  # London orange
            elif df.loc[idx, 'close'] >= df.loc[idx, 'open']:
                volume_colors.append('#2c5530')  # Bullish green
            else:
                volume_colors.append('#8B0000')  # Bearish red

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color=volume_colors,
                opacity=0.8,
                hovertemplate='Volume: %{y:,.0f}<br>Time: %{x}<extra></extra>'
            ),
            row=2, col=1
        )

    # SMC Analysis panel
    smc_y_values = []
    smc_colors = []
    smc_names = []

    for idx in df.index:
        value = 0
        color = 'gray'
        name = 'Neutral'

        if 'fvg_bullish' in df.columns and df.loc[idx, 'fvg_bullish']:
            value = 3
            color = '#28a745'
            name = 'Bullish FVG'
        elif 'fvg_bearish' in df.columns and df.loc[idx, 'fvg_bearish']:
            value = -3
            color = '#dc3545'
            name = 'Bearish FVG'
        elif 'order_block_bullish' in df.columns and df.loc[idx, 'order_block_bullish']:
            value = 2
            color = '#17a2b8'
            name = 'Bullish OB'
        elif 'order_block_bearish' in df.columns and df.loc[idx, 'order_block_bearish']:
            value = -2
            color = '#fd7e14'
            name = 'Bearish OB'
        elif 'choch' in df.columns and df.loc[idx, 'choch']:
            value = 1
            color = '#6f42c1'
            name = 'CHoCH'

        smc_y_values.append(value)
        smc_colors.append(color)
        smc_names.append(name)

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=smc_y_values,
            mode='markers',
            marker=dict(size=8, color=smc_colors),
            name='SMC Signals',
            hovertemplate='<b>%{text}</b><br>Time: %{x}<extra></extra>',
            text=smc_names
        ),
        row=3, col=1
    )

    # Wyckoff Phase Analysis
    wyckoff_colors = {
        'Accumulation': '#28a745',
        'Markup': '#17a2b8',
        'Distribution': '#ffc107',
        'Markdown': '#dc3545',
        'Unknown': '#6c757d'
    }

    if 'wyckoff_phase' in df.columns:
        wyckoff_y = []
        wyckoff_c = []
        wyckoff_text = []

        for idx in df.index:
            phase = df.loc[idx, 'wyckoff_phase']
            if phase == 'Accumulation':
                y_val = 1
            elif phase == 'Markup':
                y_val = 2
            elif phase == 'Distribution':
                y_val = 3
            elif phase == 'Markdown':
                y_val = 0
            else:
                y_val = 1.5

            wyckoff_y.append(y_val)
            wyckoff_c.append(wyckoff_colors.get(phase, '#6c757d'))
            wyckoff_text.append(phase)

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=wyckoff_y,
                mode='markers',
                marker=dict(size=6, color=wyckoff_c),
                name='Wyckoff Phase',
                hovertemplate='<b>%{text}</b><br>Time: %{x}<extra></extra>',
                text=wyckoff_text
            ),
            row=4, col=1
        )

    # Technical momentum
    if 'RSI_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['RSI_14'],
                mode='lines',
                name='RSI(14)',
                line=dict(color='#9966ff', width=2)
            ),
            row=5, col=1
        )

        fig.add_hline(y=70, line_dash="dash", line_color="red", row=5, col=1, opacity=0.5)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=5, col=1, opacity=0.5)

    # ZBAR Signal Matrix
    signal_strength = []
    for idx in df.index:
        strength = 0
        if 'midas_signal' in df.columns and df.loc[idx, 'midas_signal']:
            strength += 3
        if 'fvg_bullish' in df.columns and df.loc[idx, 'fvg_bullish']:
            strength += 1
        if 'fvg_bearish' in df.columns and df.loc[idx, 'fvg_bearish']:
            strength -= 1
        if 'london_sweep' in df.columns and df.loc[idx, 'london_sweep']:
            strength += 2

        signal_strength.append(max(-5, min(5, strength)))

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=signal_strength,
            name='Signal Strength',
            marker_color=['#dc3545' if x < 0 else '#28a745' if x > 0 else '#6c757d' for x in signal_strength],
            opacity=0.8
        ),
        row=6, col=1
    )

    # Update layout with institutional styling
    fig.update_layout(

        template='plotly_dark',
        height=1200,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="#FFD700",
            borderwidth=2
        ),
        font=dict(color='white', family='Inter'),
        paper_bgcolor='rgba(10, 15, 28, 0.95)',
        plot_bgcolor='rgba(10, 15, 28, 0.95)',
        margin=dict(l=50, r=50, t=100, b=50)
    )

    # Update all y-axes
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="SMC Level", row=3, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Wyckoff Phase", row=4, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="RSI", row=5, col=1, range=[0, 100], gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Signal Matrix", row=6, col=1, gridcolor='rgba(255,215,0,0.1)')

    fig.update_xaxes(gridcolor='rgba(255,215,0,0.1)')

    return fig

def create_strategy_summary_dashboard(midas_signals: List, smc_data: Dict, wyckoff_data: Dict, london_data: Dict) -> go.Figure:
    """Create strategy performance summary dashboard"""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Midas Model Performance',
            'SMC Signal Distribution',
            'Wyckoff Phase Distribution',
            'London Killzone Activity'
        ),
        specs=[[{"type": "scatter"}, {"type": "pie"}],
               [{"type": "pie"}, {"type": "bar"}]]
    )

    # Midas Model Performance (if signals exist)
    if midas_signals:
        timestamps = [signal['timestamp'] for signal in midas_signals]
        rr_ratios = [signal.get('rr_ratio', 2.0) for signal in midas_signals]

        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=rr_ratios,
                mode='markers+lines',
                marker=dict(size=12, color='#FFD700'),
                line=dict(color='#FFD700', width=2),
                name='Midas R:R'
            ),
            row=1, col=1
        )

    # SMC Signal Distribution
    smc_types = ['FVG Bullish', 'FVG Bearish', 'Order Block', 'CHoCH', 'BOS']
    smc_counts = [10, 8, 15, 12, 7]  # Example data

    fig.add_trace(
        go.Pie(
            labels=smc_types,
            values=smc_counts,
            hole=0.4,
            marker_colors=['#28a745', '#dc3545', '#6f42c1', '#17a2b8', '#ffc107'],
            name="SMC Distribution"
        ),
        row=1, col=2
    )

    # Wyckoff Phase Distribution
    wyckoff_phases = ['Accumulation', 'Markup', 'Distribution', 'Markdown']
    wyckoff_counts = [25, 20, 15, 10]  # Example data

    fig.add_trace(
        go.Pie(
            labels=wyckoff_phases,
            values=wyckoff_counts,
            hole=0.4,
            marker_colors=['#28a745', '#17a2b8', '#ffc107', '#dc3545'],
            name="Wyckoff Phases"
        ),
        row=2, col=1
    )

    # London Killzone Activity
    hours = [f"{h:02d}:00" for h in range(7, 17)]  # 7 AM to 4 PM UTC
    activity = [20, 35, 45, 30, 25, 15, 10, 8, 12, 18]  # Example data

    fig.add_trace(
        go.Bar(
            x=hours,
            y=activity,
            marker_color='#ff6b6b',
            name='London Activity'
        ),
        row=2, col=2
    )

    fig.update_layout(
        title="ZANFLOW v12 - Strategy Performance Dashboard",
        template='plotly_dark',
        height=600,
        font=dict(color='white', family='Inter'),
        paper_bgcolor='rgba(10, 15, 28, 0.95)',
        showlegend=False
    )

    return fig

# ============================================================================
# DATA LOADING AND PROCESSING
# ============================================================================


# New cached function to get available parquet files
@st.cache_data(ttl=300)
def get_available_parquet_files():
    return load_available_parquet_files(PARQUET_DATA_DIR)

# Function to load data for a given symbol and timeframe
@st.cache_data(ttl=300)
def load_enriched_timeframes(selected_symbol, selected_timeframe):
    """Load all available timeframe data for selected symbol and timeframe with advanced caching (no widgets here)"""
    available_files = get_available_parquet_files()
    if not available_files:
        return {}, {}
    # Find file for symbol/timeframe
    selected_file = next((f for sym, tf, f in available_files if sym == selected_symbol and tf == selected_timeframe), None)
    data = {}
    stats = {}
    if selected_file:
        try:
            df = pd.read_parquet(selected_file)
            # Ensure proper datetime index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            df.columns = df.columns.str.lower()
            required_cols = ['open', 'high', 'low', 'close']
            # Remove Streamlit widget calls here
            if not all(col in df.columns for col in required_cols):
                # Do not use st.warning here. Just skip or log.
                pass
            else:
                data[selected_timeframe] = df
                stats[selected_timeframe] = {
                    'bars': len(df),
                    'indicators': len(df.columns),
                    'date_range': f"{df.index.min().date()} to {df.index.max().date()}",
                    'last_price': df['close'].iloc[-1],
                    'daily_change': ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                }
        except Exception as e:
            # Do not use st.warning here. Just skip or log.
            pass
    return data, stats

def process_zanflow_analysis(df: pd.DataFrame, timeframe: str) -> Tuple[pd.DataFrame, Dict, List]:
    """Process comprehensive ZANFLOW v12 analysis"""

    # Initialize analysis engines
    midas_detector = MidasModelDetector()
    london_analyzer = LondonKillzoneAnalyzer()
    smc_analyzer = SMCAnalyzer()
    wyckoff_analyzer = WyckoffAnalyzer()

    # Run comprehensive analysis
    try:
        # Midas Model Detection (Gold-specific)
        df_analyzed = midas_detector.detect_midas_setups(df)

        # London Killzone Analysis
        df_analyzed = london_analyzer.analyze_london_session(df_analyzed)

        # SMC Analysis
        df_analyzed = smc_analyzer.analyze_smc_structure(df_analyzed)

        # Wyckoff Analysis
        df_analyzed = wyckoff_analyzer.analyze_wyckoff_structure(df_analyzed)

        # Compile analysis results
        analysis_results = {
            'midas_signals': midas_detector.signals,
            'smc_data': {
                'fair_value_gaps': smc_analyzer.fair_value_gaps,
                'order_blocks': smc_analyzer.order_blocks,
                'liquidity_zones': smc_analyzer.liquidity_zones
            },
            'wyckoff_data': {
                'phases': wyckoff_analyzer.phases,
                'events': wyckoff_analyzer.events
            },
            'london_data': {
                'signals': london_analyzer.signals
            }
        }

        # Generate ZBAR logs
        zbar_logs = generate_zbar_logs(df_analyzed, analysis_results, timeframe)

        return df_analyzed, analysis_results, zbar_logs

    except Exception as e:
        st.error(f"Error in ZANFLOW analysis: {e}")
        return df, {}, []

def generate_zbar_logs(df: pd.DataFrame, analysis: Dict, timeframe: str) -> List[Dict]:
    """Generate ZBAR (Zanalytics Behavioral Analysis and Reflection) logs"""
    logs = []

    # Midas signal logs
    for signal in analysis.get('midas_signals', []):
        logs.append({
            'timestamp': signal['timestamp'].isoformat(),
            'strategy': 'MIDAS_MODEL',
            'timeframe': timeframe,
            'signal_type': signal['direction'].upper(),
            'entry_price': signal['entry'],
            'stop_loss': signal['stop'],
            'target': signal['target'],
            'risk_reward': signal['rr_ratio'],
            'window': signal['window'],
            'confidence': 'HIGH',
            'session': 'NY_EVENING'
        })

    # SMC signal logs
    fvg_count = len(analysis.get('smc_data', {}).get('fair_value_gaps', []))
    ob_count = len(analysis.get('smc_data', {}).get('order_blocks', []))

    if fvg_count > 0 or ob_count > 0:
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'strategy': 'SMC_ANALYSIS',
            'timeframe': timeframe,
            'fvg_count': fvg_count,
            'order_block_count': ob_count,
            'market_structure': 'ACTIVE',
            'confidence': 'MEDIUM'
        })

    # Wyckoff phase logs
    if df['wyckoff_phase'].value_counts().index[0] != 'Unknown':
        dominant_phase = df['wyckoff_phase'].value_counts().index[0]
        logs.append({
            'timestamp': datetime.now().isoformat(),
            'strategy': 'WYCKOFF_ANALYSIS',
            'timeframe': timeframe,
            'dominant_phase': dominant_phase,
            'phase_strength': df['wyckoff_phase'].value_counts().iloc[0] / len(df),
            'confidence': 'MEDIUM'
        })

    return logs

# ============================================================================
# MAIN STREAMLIT APPLICATION
# ============================================================================

def main():
    """Main ZANFLOW v12 Institutional Dashboard Application"""

    # Setup institutional page (styling only)
    setup_institutional_page()

    # Institutional Header
    st.markdown("""
        <div class="institutional-header">
            <h1>🏛️ ZANFLOW v12</h1>
            <h2>INSTITUTIONAL GRADE TRADING DASHBOARD</h2>
            <p>Advanced SMC • Midas Model • London Killzone • Wyckoff Analysis</p>
            <p><strong>QUAD DESTROYER PRO • ULTRA-VISUAL ANALYSIS</strong></p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar: Symbol & Timeframe controls (widgets OUTSIDE cached functions)
    available_files = get_available_parquet_files()
    symbols = sorted(set(sym for sym, tf, _ in available_files))
    selected_symbol = st.sidebar.selectbox("📈 Select Symbol", symbols, index=0)
    tfs = sorted(set(tf for sym, tf, _ in available_files if sym == selected_symbol))
    selected_timeframe = st.sidebar.selectbox("⏱️ Select Timeframe", tfs, index=len(tfs)-1)

    # Add Load Data button below Select Timeframe
    load_data_clicked = st.sidebar.button("🔄 Load Data")

    # Only load the data after clicking "Load Data"
    data = {}
    stats = {}
    if load_data_clicked:
        with st.spinner("🔄 Loading ZANFLOW v12 enriched datasets..."):
            data, stats = load_enriched_timeframes(selected_symbol, selected_timeframe)
            # Save to session state for persistent access between runs
            st.session_state['zanflow_data'] = data
            st.session_state['zanflow_stats'] = stats
            st.session_state['zanflow_symbol'] = selected_symbol
            st.session_state['zanflow_timeframe'] = selected_timeframe
    else:
        # On normal rerun, try to load previous data from session_state
        data = st.session_state.get('zanflow_data', {})
        stats = st.session_state.get('zanflow_stats', {})
        selected_symbol = st.session_state.get('zanflow_symbol', selected_symbol)
        selected_timeframe = st.session_state.get('zanflow_timeframe', selected_timeframe)

    if (not load_data_clicked) and (not data):
        st.info("👈 Please select Symbol/Timeframe and click '🔄 Load Data' to begin.")
        return

    if not data:
        st.error("❌ No enriched data found. Please ensure Parquet files are available.")
        return

    # Allow user to choose number of candles
    df_len = list(data.values())[0].shape[0] if data else 500
    lookback = st.sidebar.slider("🔁 Number of Candles", 20, df_len, min(500, df_len))
    current_df = list(data.values())[0].tail(lookback)

    # Sidebar configuration
    with st.sidebar:
        st.markdown("### 🎛️ ZANFLOW v12 Controls")

        # Strategy selection
        st.markdown("### 🎯 Strategy Configuration")

        enable_midas = st.checkbox("🥇 Midas Model (Gold-Specific)", value=True,
                                  help="8PM/9PM NY mechanical gold strategy")
        enable_london = st.checkbox("🇬🇧 London Killzone", value=True,
                                   help="London session liquidity analysis")
        enable_smc = st.checkbox("🧠 Smart Money Concepts", value=True,
                                help="FVG, Order Blocks, Market Structure")
        enable_wyckoff = st.checkbox("📈 Wyckoff Method", value=True,
                                    help="Accumulation/Distribution phases")

        # Display options
        st.markdown("### 🎨 Display Options")

        show_all_timeframes = st.checkbox("Multi-Timeframe View", value=False)
        show_zbar_logs = st.checkbox("ZBAR Logs", value=True)
        show_summary_dashboard = st.checkbox("Strategy Summary", value=True)

        # Current market status
        st.markdown("---")
        st.markdown("### 📊 Market Status")

        current_time = datetime.now(pytz.timezone('America/New_York'))
        is_market_hours = 9 <= current_time.hour <= 16 and current_time.weekday() < 5

        status_color = "🟢" if is_market_hours else "🔴"
        status_text = "MARKET OPEN" if is_market_hours else "MARKET CLOSED"

        st.markdown(f"**{status_color} {status_text}**")
        st.markdown(f"**NY Time:** {current_time.strftime('%H:%M:%S')}")

        # Data statistics
        if selected_timeframe in stats:
            st.markdown("### 📈 Data Statistics")
            stat = stats[selected_timeframe]
            st.metric("Bars Loaded", f"{stat['bars']:,}")
            st.metric("Indicators", stat['indicators'])
            st.metric("Last Price", f"${stat['last_price']:.2f}")

    # Display current price and key metrics
    latest = current_df.iloc[-1]
    current_price = latest['close']

    if len(current_df) > 1:
        price_change = current_price - current_df.iloc[-2]['close']
        price_change_pct = (price_change / current_df.iloc[-2]['close']) * 100
    else:
        price_change = 0
        price_change_pct = 0

    # Key metrics display
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class="metric-institutional">
                <div class="price-display-institutional">${price_fmt(current_price, selected_symbol)}</div>
                <div>{selected_symbol} Current Price</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        change_color = "#28a745" if price_change >= 0 else "#dc3545"
        st.markdown(f"""
            <div class="metric-institutional">
                <div style="color: {change_color}; font-size: 2rem; font-weight: bold;">
                    {price_fmt(price_change, selected_symbol)}
                </div>
                <div>Change ({price_change_pct:+.2f}%)</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-institutional">
                <div style="font-size: 2rem; font-weight: bold; color: #FFD700;">
                    ${price_fmt(latest['high'], selected_symbol)}
                </div>
                <div>Session High</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="metric-institutional">
                <div style="font-size: 2rem; font-weight: bold; color: #FF8C00;">
                    ${price_fmt(latest['low'], selected_symbol)}
                </div>
                <div>Session Low</div>
            </div>
        """, unsafe_allow_html=True)

    # Run ZANFLOW analysis
    if st.button("🚀 Execute ZANFLOW v12 Analysis", type="primary"):
        with st.spinner("🧠 Running institutional-grade analysis..."):
            analyzed_df, analysis_results, zbar_logs = process_zanflow_analysis(current_df, selected_timeframe)

        # Display active signals
        st.subheader("🎯 Active Trading Signals")

        # Midas signals
        if enable_midas and analysis_results.get('midas_signals'):
            for signal in analysis_results['midas_signals'][-3:]:  # Show last 3
                st.markdown(f"""
                    <div class="midas-signal">
                        <h3>🥇 MIDAS MODEL SIGNAL DETECTED</h3>
                        <p><strong>Window:</strong> {signal['window']} NY | <strong>Direction:</strong> {signal['direction'].upper()}</p>
                        <p><strong>Entry:</strong> ${price_fmt(signal['entry'], selected_symbol)} | <strong>Stop:</strong> ${price_fmt(signal['stop'], selected_symbol)} | <strong>Target:</strong> ${price_fmt(signal['target'], selected_symbol)}</p>
                        <p><strong>Risk:Reward:</strong> 1:{signal['rr_ratio']:.1f} | <strong>Time:</strong> {signal['timestamp'].strftime('%Y-%m-%d %H:%M')}</p>
                    </div>
                """, unsafe_allow_html=True)

        # London Killzone signals
        if enable_london and 'london_sweep' in analyzed_df.columns:
            london_sweeps = analyzed_df[analyzed_df['london_sweep'] == True]
            if not london_sweeps.empty:
                st.markdown(f"""
                    <div class="london-killzone">
                        <h3>🇬🇧 LONDON KILLZONE ACTIVITY</h3>
                        <p><strong>Liquidity Sweeps Detected:</strong> {len(london_sweeps)}</p>
                        <p><strong>Last Sweep:</strong> {london_sweeps.index[-1].strftime('%Y-%m-%d %H:%M')}</p>
                        <p><strong>Asian Session Liquidity:</strong> Active monitoring</p>
                    </div>
                """, unsafe_allow_html=True)

        # SMC Analysis
        if enable_smc:
            smc_data = analysis_results.get('smc_data', {})
            fvg_count = len(smc_data.get('fair_value_gaps', []))
            ob_count = len(smc_data.get('order_blocks', []))

            st.markdown("### 🧠 Smart Money Concepts Analysis")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                    <div class="smc-indicator fvg-bullish">
                        <h4>📈 Fair Value Gaps</h4>
                        <p><strong>Total Detected:</strong> {fvg_count}</p>
                        <p><strong>Status:</strong> {'Active' if fvg_count > 0 else 'None'}</p>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div class="smc-indicator order-block">
                        <h4>📦 Order Blocks</h4>
                        <p><strong>Total Detected:</strong> {ob_count}</p>
                        <p><strong>Status:</strong> {'Active' if ob_count > 0 else 'None'}</p>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                liquidity_count = len(smc_data.get('liquidity_zones', []))
                st.markdown(f"""
                    <div class="smc-indicator liquidity-zone">
                        <h4>💧 Liquidity Zones</h4>
                        <p><strong>Total Detected:</strong> {liquidity_count}</p>
                        <p><strong>Status:</strong> {'Active' if liquidity_count > 0 else 'None'}</p>
                    </div>
                """, unsafe_allow_html=True)

        # Wyckoff Analysis
        if enable_wyckoff and 'wyckoff_phase' in analyzed_df.columns:
            current_phase = analyzed_df['wyckoff_phase'].iloc[-1]
            phase_distribution = analyzed_df['wyckoff_phase'].value_counts()

            st.markdown("### 📈 Wyckoff Market Analysis")

            # Current phase display
            phase_class = current_phase.lower()
            st.markdown(f"""
                <div class="strategy-card">
                    <h4>Current Market Phase</h4>
                    <div class="wyckoff-phase {phase_class}">
                        {current_phase.upper()}
                    </div>
                    <p><strong>Phase Distribution:</strong></p>
            """, unsafe_allow_html=True)

            for phase, count in phase_distribution.head(3).items():
                percentage = (count / len(analyzed_df)) * 100
                st.markdown(f"• **{phase}**: {percentage:.1f}% ({count} bars)")

            st.markdown("</div>", unsafe_allow_html=True)

        # Main institutional chart
        st.markdown('<div class="chart-container-pro">', unsafe_allow_html=True)
        st.subheader("📊 ZANFLOW v12 Master Chart")

        master_chart = create_institutional_master_chart(
            analyzed_df, selected_symbol, selected_timeframe,
            analysis_results.get('midas_signals', []),
            analysis_results.get('smc_data', {}),
            analysis_results.get('wyckoff_data', {})
        )

        st.plotly_chart(master_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Strategy summary dashboard
        if show_summary_dashboard:
            st.subheader("📈 Strategy Performance Dashboard")

            summary_chart = create_strategy_summary_dashboard(
                analysis_results.get('midas_signals', []),
                analysis_results.get('smc_data', {}),
                analysis_results.get('wyckoff_data', {}),
                analysis_results.get('london_data', {})
            )

            st.plotly_chart(summary_chart, use_container_width=True)

        # Multi-timeframe analysis
        if show_all_timeframes:
            st.subheader("🔄 Multi-Timeframe Signal Matrix")

            mtf_cols = st.columns(len(data))
            for i, (tf, df_tf) in enumerate(data.items()):
                with mtf_cols[i]:
                    # Quick analysis for each timeframe
                    tf_analyzed, tf_results, _ = process_zanflow_analysis(df_tf.tail(100), tf)

                    midas_count = len(tf_results.get('midas_signals', []))
                    smc_count = len(tf_results.get('smc_data', {}).get('fair_value_gaps', []))

                    signal_strength = "HIGH" if midas_count > 0 else "MEDIUM" if smc_count > 0 else "LOW"
                    signal_color = "#28a745" if signal_strength == "HIGH" else "#ffc107" if signal_strength == "MEDIUM" else "#6c757d"

                    st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; text-align: center; border: 2px solid {signal_color};">
                            <h4>{tf.upper()}</h4>
                            <div style="color: {signal_color}; font-weight: bold; font-size: 1.2rem;">
                                {signal_strength}
                            </div>
                            <div>Midas: {midas_count}</div>
                            <div>SMC: {smc_count}</div>
                            <div>Price: ${price_fmt(df_tf.iloc[-1]['close'], selected_symbol)}</div>
                        </div>
                    """, unsafe_allow_html=True)

        # ZBAR Logs
        if show_zbar_logs and zbar_logs:
            st.subheader("📊 ZBAR Analysis Logs")

            # Format prices in logs using price_fmt where possible
            def _format_log_prices(log):
                for k in ['entry_price', 'stop_loss', 'target']:
                    if k in log:
                        try:
                            log[k] = price_fmt(log[k], selected_symbol)
                        except Exception:
                            pass
                return log

            for log in zbar_logs[-5:]:  # Show last 5 logs
                log_fmt = _format_log_prices(dict(log))
                st.markdown(f"""
                    <div class="zabar-log">
                        <strong>[{log_fmt['strategy']}]</strong> {log_fmt['timestamp']}<br>
                        {json.dumps(log_fmt, indent=2)}
                    </div>
                """, unsafe_allow_html=True)

        # Export functionality
        st.subheader("💾 Export Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 Export ZBAR Logs"):
                # Format prices in logs for export
                def _format_log_prices(log):
                    for k in ['entry_price', 'stop_loss', 'target']:
                        if k in log:
                            try:
                                log[k] = price_fmt(log[k], selected_symbol)
                            except Exception:
                                pass
                    return log
                logs_json = json.dumps([_format_log_prices(dict(log)) for log in zbar_logs], indent=2, default=str)
                st.download_button(
                    label="Download ZBAR Logs",
                    data=logs_json,
                    file_name=f"zanflow_v12_zbar_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

        with col2:
            if st.button("📊 Export Analysis Data"):
                analysis_json = json.dumps(analysis_results, indent=2, default=str)
                st.download_button(
                    label="Download Analysis",
                    data=analysis_json,
                    file_name=f"zanflow_v12_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

        with col3:
            if st.button("📈 Export Chart Data"):
                # Format price columns using price_fmt if desired (optional)
                csv_data = analyzed_df.to_csv()
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"zanflow_v12_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #888;">
            <p><strong>🏛️ ZANFLOW v12 - Institutional Grade Trading Dashboard</strong></p>
            <p>Advanced SMC • Midas Model • London Killzone • Wyckoff Analysis</p>
            <p>QUAD DESTROYER PRO • ULTRA-VISUAL PROFESSIONAL TRADING INTERFACE</p>
            <p><em>Built for institutional traders and advanced market participants</em></p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()