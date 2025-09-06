#!/usr/bin/env python3
"""
ncOS Ultimate Microstructure Analyzer - Enhanced Edition
Integrating ZANFLOW v12 architecture with advanced SMC analysis and London Kill Zone detection
ALL FEATURES ENABLED BY DEFAULT
"""

import os
import re
from pathlib import Path
from statsmodels.stats.diagnostic import acorr_ljungbox
import pandas as pd
import numpy as np
import json
import argparse
import sys
from datetime import datetime, timedelta
import warnings
import yaml
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from functools import partial
import logging
from scipy import stats
import statsmodels.api as sm
import types

if not hasattr(stats, "diagnostic"):
    diag_mod = types.ModuleType("diagnostic")
    diag_mod.acorr_ljungbox = sm.stats.acorr_ljungbox
    setattr(stats, "diagnostic", diag_mod)

from scipy.signal import find_peaks, savgol_filter
from scipy.optimize import minimize
import sqlite3
import pickle
import gzip
from collections import defaultdict, deque
import talib
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from statsmodels.tsa.stattools import adfuller

def add_fuller(series):
    """
    Augmented Dickey-Fuller test for stationarity.
    Returns a dict with test statistic, p-value, and used lags.
    """
    try:
        result = adfuller(series, autolag='AIC')
        return {
            'adf_statistic': result[0],
            'p_value': result[1],
            'used_lag': result[2],
            'n_obs': result[3],
            'critical_values': result[4],
            'ic_best': result[5] if len(result) > 5 else None
        }
    except Exception as e:
        return {'error': str(e)}

def extract_symbol_from_filename(filename: str) -> str:
    """
    Extract trading symbol from filenames like 'BTCUSD_M1_bars.csv'.
    Returns 'UNKNOWN' if the pattern is missing.
    """
    base = os.path.basename(filename)
    if '_' in base:
        return base.split('_')[0].upper()
    return 'UNKNOWN'

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ncOS_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AnalysisConfig:
    """Ultimate configuration for maximum analysis - ALL FEATURES ENABLED BY DEFAULT"""
    # Data processing
    process_tick_data: bool = True
    process_csv_files: bool = True
    process_json_files: bool = True
    tick_bars_limit: int = 1500  # DEFAULT 1500 TICK BARS
    bar_limits: Dict[str, int] = field(default_factory=lambda: {
        '1min': 1000, '5min': 500, '15min': 200, '30min': 100,
        '1h': 100, '4h': 50, '1d': 30, '1w': 20, '1M': 12
    })

    # Technical analysis - ALL ENABLED
    enable_all_indicators: bool = True
    enable_advanced_patterns: bool = True
    enable_harmonic_patterns: bool = True
    enable_elliott_waves: bool = True
    enable_gann_analysis: bool = True
    enable_fibonacci_analysis: bool = True

    # Market structure - ALL ENABLED
    enable_smc_analysis: bool = True
    enable_wyckoff_analysis: bool = True
    enable_volume_profile: bool = True
    enable_order_flow: bool = True
    enable_market_profile: bool = True

    # Microstructure analysis - ALL ENABLED
    enable_liquidity_analysis: bool = True
    enable_manipulation_detection: bool = True
    enable_spoofing_detection: bool = True
    enable_front_running_detection: bool = True
    enable_wash_trading_detection: bool = True

    # Machine learning - ALL ENABLED
    enable_ml_predictions: bool = True
    enable_anomaly_detection: bool = True
    enable_clustering: bool = True
    enable_regime_detection: bool = True

    # Risk management - ALL ENABLED
    enable_risk_metrics: bool = True
    enable_portfolio_analysis: bool = True
    enable_stress_testing: bool = True
    enable_var_calculation: bool = True

    # Visualization - ALL ENABLED
    enable_advanced_plots: bool = True
    enable_interactive_charts: bool = True
    enable_3d_visualization: bool = True
    save_all_plots: bool = True

    # Output options - ALL ENABLED
    compress_output: bool = True
    save_detailed_reports: bool = True
    export_excel: bool = True
    export_csv: bool = True

class UltimateIndicatorEngine:
    """Maximum indicator calculation engine with enhanced London Kill Zone detection"""
    
    # --- Updated: UltimateIndicatorEngine.__init__ ---
    def __init__(self, logger_instance=None):
        self.indicators = {}
        # Use provided logger or fall back to a default if none is provided
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)

    # --- Updated: UltimateIndicatorEngine._add_quick_enrichment ---
    def _add_quick_enrichment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Inject lightweight enrichments including ATR, cumulative VWAP,
        and enhanced UTC session tags, including the London Kill Zone.
        """
        try:
            import pandas_ta as ta
        except ImportError:
            ta = None

        if ta and all(c in df.columns for c in ("high", "low", "close")):
            try:
                df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            except Exception as e:
                self.logger.warning(f"Error calculating ATR-14: {e}")
                pass

        if all(c in df.columns for c in ("close", "volume")):
            try:
                df["vwap_d"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
            except Exception as e:
                self.logger.warning(f"Error calculating VWAP: {e}")
                pass

        try:
            utc_hours = df.index.tz_convert("UTC").hour
            # Existing session mapping
            df["session"] = utc_hours.map(
                lambda h: "US" if 13 <= h < 22 else ("EU" if 7 <= h < 13 else "AS")
            )
            # New: London Kill Zone identification
            # London Kill Zone starts with London session (EU) and closes at 13:00 UTC.
            # This implies UTC hours from 7:00 (inclusive) to 13:00 (exclusive).
            df["is_london_killzone"] = (utc_hours >= 7) & (utc_hours < 13)
        except Exception as e:
            self.logger.warning(f"Error adding session/killzone enrichment: {e}")
            pass

        return df

    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Calculate over 200 technical indicators"""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        open_prices = df['open'].values
        volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

        indicators = {}

        # Price-based indicators
        indicators.update(self._price_indicators(high, low, close, open_prices))

        # Volume indicators
        indicators.update(self._volume_indicators(high, low, close, volume))

        # Momentum indicators
        indicators.update(self._momentum_indicators(high, low, close))

        # Volatility indicators
        indicators.update(self._volatility_indicators(high, low, close))

        # Cycle indicators
        indicators.update(self._cycle_indicators(close))

        # Statistical indicators
        indicators.update(self._statistical_indicators(close))

        # Custom indicators
        indicators.update(self._custom_indicators(high, low, close, open_prices, volume))
        
        # Apply quick enrichment
        df = self._add_quick_enrichment(df)
        return indicators

    def _price_indicators(self, high, low, close, open_prices):
        """Price-based indicators"""
        indicators = {}

        # Moving averages (multiple periods)
        for period in [5, 10, 20, 50, 100, 200]:
            try:
                indicators[f'SMA_{period}'] = talib.SMA(close, timeperiod=period)
                indicators[f'EMA_{period}'] = talib.EMA(close, timeperiod=period)
                indicators[f'WMA_{period}'] = talib.WMA(close, timeperiod=period)
                indicators[f'TEMA_{period}'] = talib.TEMA(close, timeperiod=period)
                indicators[f'TRIMA_{period}'] = talib.TRIMA(close, timeperiod=period)
                indicators[f'KAMA_{period}'] = talib.KAMA(close, timeperiod=period)
                indicators[f'MAMA_{period}'], indicators[f'FAMA_{period}'] = talib.MAMA(close)
            except:
                pass

        # Bollinger Bands (multiple periods)
        for period in [10, 20, 50]:
            try:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=period)
                indicators[f'BB_UPPER_{period}'] = bb_upper
                indicators[f'BB_MIDDLE_{period}'] = bb_middle
                indicators[f'BB_LOWER_{period}'] = bb_lower
                indicators[f'BB_WIDTH_{period}'] = (bb_upper - bb_lower) / bb_middle
                indicators[f'BB_POSITION_{period}'] = (close - bb_lower) / (bb_upper - bb_lower)
            except:
                pass

        # Donchian Channels
        for period in [10, 20, 55]:
            try:
                indicators[f'DONCHIAN_UPPER_{period}'] = pd.Series(high).rolling(period).max().values
                indicators[f'DONCHIAN_LOWER_{period}'] = pd.Series(low).rolling(period).min().values
                indicators[f'DONCHIAN_MIDDLE_{period}'] = (indicators[f'DONCHIAN_UPPER_{period}'] + indicators[f'DONCHIAN_LOWER_{period}']) / 2
            except:
                pass

        # Pivot Points
        try:
            indicators['PIVOT'] = (high + low + close) / 3
            indicators['R1'] = 2 * indicators['PIVOT'] - low
            indicators['S1'] = 2 * indicators['PIVOT'] - high
            indicators['R2'] = indicators['PIVOT'] + (high - low)
            indicators['S2'] = indicators['PIVOT'] - (high - low)
            indicators['R3'] = high + 2 * (indicators['PIVOT'] - low)
            indicators['S3'] = low - 2 * (high - indicators['PIVOT'])
        except:
            pass

        return indicators

    def _volume_indicators(self, high, low, close, volume):
        """Volume-based indicators"""
        indicators = {}

        try:
            # Volume indicators
            indicators['OBV'] = talib.OBV(close, volume)
            indicators['AD'] = talib.AD(high, low, close, volume)
            indicators['ADOSC'] = talib.ADOSC(high, low, close, volume)

            # Volume moving averages
            for period in [10, 20, 50]:
                indicators[f'VOLUME_SMA_{period}'] = talib.SMA(volume, timeperiod=period)
                indicators[f'VOLUME_RATIO_{period}'] = volume / indicators[f'VOLUME_SMA_{period}']

            # Volume price trend
            indicators['VPT'] = np.cumsum(volume * (close - np.roll(close, 1)) / np.roll(close, 1))

            # Money flow index
            indicators['MFI_14'] = talib.MFI(high, low, close, volume, timeperiod=14)

            # Volume weighted average price
            indicators['VWAP'] = np.cumsum(volume * close) / np.cumsum(volume)

        except:
            pass

        return indicators

    def _momentum_indicators(self, high, low, close):
        """Momentum indicators"""
        indicators = {}

        try:
            # RSI (multiple periods)
            for period in [9, 14, 21]:
                indicators[f'RSI_{period}'] = talib.RSI(close, timeperiod=period)

            # Stochastic
            indicators['STOCH_K'], indicators['STOCH_D'] = talib.STOCH(high, low, close)
            indicators['STOCHF_K'], indicators['STOCHF_D'] = talib.STOCHF(high, low, close)
            indicators['STOCHRSI_K'], indicators['STOCHRSI_D'] = talib.STOCHRSI(close)

            # MACD (multiple settings)
            for fast, slow, signal in [(12, 26, 9), (5, 35, 5), (19, 39, 9)]:
                macd, signal_line, histogram = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal)
                indicators[f'MACD_{fast}_{slow}_{signal}'] = macd
                indicators[f'MACD_SIGNAL_{fast}_{slow}_{signal}'] = signal_line
                indicators[f'MACD_HIST_{fast}_{slow}_{signal}'] = histogram

            # Williams %R
            for period in [14, 21]:
                indicators[f'WILLR_{period}'] = talib.WILLR(high, low, close, timeperiod=period)

            # Commodity Channel Index
            for period in [14, 20]:
                indicators[f'CCI_{period}'] = talib.CCI(high, low, close, timeperiod=period)

            # Ultimate Oscillator
            indicators['ULTOSC'] = talib.ULTOSC(high, low, close)

            # Rate of Change
            for period in [10, 20]:
                indicators[f'ROC_{period}'] = talib.ROC(close, timeperiod=period)
                indicators[f'ROCP_{period}'] = talib.ROCP(close, timeperiod=period)
                indicators[f'ROCR_{period}'] = talib.ROCR(close, timeperiod=period)

            # Momentum
            for period in [10, 14, 20]:
                indicators[f'MOM_{period}'] = talib.MOM(close, timeperiod=period)

        except:
            pass

        return indicators

    def _volatility_indicators(self, high, low, close):
        """Volatility indicators"""
        indicators = {}

        try:
            # Average True Range
            for period in [14, 21]:
                indicators[f'ATR_{period}'] = talib.ATR(high, low, close, timeperiod=period)
                indicators[f'NATR_{period}'] = talib.NATR(high, low, close, timeperiod=period)
                indicators[f'TRANGE_{period}'] = talib.TRANGE(high, low, close)

            # Standard deviation
            for period in [10, 20, 50]:
                indicators[f'STDDEV_{period}'] = talib.STDDEV(close, timeperiod=period)
                indicators[f'VAR_{period}'] = talib.VAR(close, timeperiod=period)

            # Chaikin Volatility
            indicators['CHAIKIN_VOL'] = ((high - low).rolling(10).mean().pct_change(10) * 100)

        except:
            pass

        return indicators

    def _cycle_indicators(self, close):
        """Cycle indicators"""
        indicators = {}

        try:
            # Hilbert Transform indicators
            indicators['HT_DCPERIOD'] = talib.HT_DCPERIOD(close)
            indicators['HT_DCPHASE'] = talib.HT_DCPHASE(close)
            indicators['HT_PHASOR_INPHASE'], indicators['HT_PHASOR_QUADRATURE'] = talib.HT_PHASOR(close)
            indicators['HT_SINE_SINE'], indicators['HT_SINE_LEADSINE'] = talib.HT_SINE(close)
            indicators['HT_TRENDMODE'] = talib.HT_TRENDMODE(close)

        except:
            pass

        return indicators

    def _statistical_indicators(self, close):
        """Statistical indicators"""
        indicators = {}

        try:
            # Linear regression
            for period in [14, 20, 50]:
                indicators[f'LINEARREG_{period}'] = talib.LINEARREG(close, timeperiod=period)
                indicators[f'LINEARREG_ANGLE_{period}'] = talib.LINEARREG_ANGLE(close, timeperiod=period)
                indicators[f'LINEARREG_INTERCEPT_{period}'] = talib.LINEARREG_INTERCEPT(close, timeperiod=period)
                indicators[f'LINEARREG_SLOPE_{period}'] = talib.LINEARREG_SLOPE(close, timeperiod=period)

            # Time Series Forecast
            for period in [14, 20]:
                indicators[f'TSF_{period}'] = talib.TSF(close, timeperiod=period)

            # Beta
            indicators['BETA'] = talib.BETA(close, close, timeperiod=5)
            indicators['CORREL'] = talib.CORREL(close, close, timeperiod=30)

        except:
            pass

        return indicators

    def _custom_indicators(self, high, low, close, open_prices, volume):
        """Custom advanced indicators"""
        indicators = {}

        try:
            # Heikin Ashi
            ha_close = (open_prices + high + low + close) / 4
            ha_open = np.zeros_like(open_prices)
            ha_open[0] = (open_prices[0] + close[0]) / 2
            for i in range(1, len(ha_open)):
                ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
            ha_high = np.maximum(high, np.maximum(ha_open, ha_close))
            ha_low = np.minimum(low, np.minimum(ha_open, ha_close))

            indicators['HA_OPEN'] = ha_open
            indicators['HA_HIGH'] = ha_high
            indicators['HA_LOW'] = ha_low
            indicators['HA_CLOSE'] = ha_close

            # Ichimoku Cloud
            tenkan_sen = (pd.Series(high).rolling(9).max() + pd.Series(low).rolling(9).min()) / 2
            kijun_sen = (pd.Series(high).rolling(26).max() + pd.Series(low).rolling(26).min()) / 2
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
            senkou_span_b = ((pd.Series(high).rolling(52).max() + pd.Series(low).rolling(52).min()) / 2).shift(26)
            chikou_span = pd.Series(close).shift(-26)

            indicators['TENKAN_SEN'] = tenkan_sen.values
            indicators['KIJUN_SEN'] = kijun_sen.values
            indicators['SENKOU_SPAN_A'] = senkou_span_a.values
            indicators['SENKOU_SPAN_B'] = senkou_span_b.values
            indicators['CHIKOU_SPAN'] = chikou_span.values

            # Parabolic SAR
            indicators['SAR'] = talib.SAR(high, low)
            indicators['SAREXT'] = talib.SAREXT(high, low)

            # SuperTrend
            for period, multiplier in [(10, 3), (14, 2), (20, 1.5)]:
                hl2 = (high + low) / 2
                atr = talib.ATR(high, low, close, timeperiod=period)
                upper_band = hl2 + multiplier * atr
                lower_band = hl2 - multiplier * atr

                supertrend = np.zeros_like(close)
                direction = np.ones_like(close)

                for i in range(1, len(close)):
                    if close[i] > upper_band[i-1]:
                        direction[i] = 1
                    elif close[i] < lower_band[i-1]:
                        direction[i] = -1
                    else:
                        direction[i] = direction[i-1]

                    if direction[i] == 1:
                        supertrend[i] = lower_band[i]
                    else:
                        supertrend[i] = upper_band[i]

                indicators[f'SUPERTREND_{period}_{multiplier}'] = supertrend
                indicators[f'SUPERTREND_DIR_{period}_{multiplier}'] = direction

        except Exception as e:
            self.logger.warning(f"Error calculating custom indicators: {e}")

        return indicators

class HarmonicPatternDetector:
    """Advanced harmonic pattern detection"""

    # --- Updated: HarmonicPatternDetector.__init__ ---
    def __init__(self, logger_instance=None):
        self.patterns = {
            'GARTLEY': {'XA': 0.618, 'AB': 0.382, 'BC': 0.886, 'CD': 0.786},
            'BUTTERFLY': {'XA': 0.786, 'AB': 0.382, 'BC': 0.886, 'CD': 1.27},
            'BAT': {'XA': 0.382, 'AB': 0.382, 'BC': 0.886, 'CD': 0.886},
            'CRAB': {'XA': 0.382, 'AB': 0.382, 'BC': 0.886, 'CD': 1.618},
            'SHARK': {'XA': 0.5, 'AB': 0.5, 'BC': 1.618, 'CD': 0.886},
            'CYPHER': {'XA': 0.382, 'AB': 0.382, 'BC': 1.272, 'CD': 0.786},
            'THREE_DRIVES': {'XA': 0.618, 'AB': 0.618, 'BC': 0.618, 'CD': 0.786},
            'ABCD': {'AB': 0.618, 'BC': 0.618, 'CD': 1.272}
        }
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)

    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """Detect all harmonic patterns"""
        patterns_found = []

        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            # Find pivot points
            pivots = self._find_pivots(high, low, close)

            # Check for patterns
            for pattern_name, ratios in self.patterns.items():
                pattern_results = self._check_pattern(pivots, ratios, pattern_name)
                patterns_found.extend(pattern_results)

        except Exception as e:
            self.logger.warning(f"Error detecting harmonic patterns: {e}")

        return patterns_found

    def _find_pivots(self, high, low, close, window=5):
        """Find pivot points"""
        pivots = []

        for i in range(window, len(high) - window):
            # Pivot high
            if all(high[i] >= high[i-j] for j in range(1, window+1)) and                all(high[i] >= high[i+j] for j in range(1, window+1)):
                pivots.append({'index': i, 'price': high[i], 'type': 'high'})

            # Pivot low
            if all(low[i] <= low[i-j] for j in range(1, window+1)) and                all(low[i] <= low[i+j] for j in range(1, window+1)):
                pivots.append({'index': i, 'price': low[i], 'type': 'low'})

        return sorted(pivots, key=lambda x: x['index'])

    def _check_pattern(self, pivots, ratios, pattern_name):
        """Check for specific harmonic pattern"""
        patterns = []

        if len(pivots) < 5:
            return patterns

        # Check all possible 5-point combinations
        for i in range(len(pivots) - 4):
            points = pivots[i:i+5]

            # Validate pattern structure
            if self._validate_pattern_structure(points, ratios):
                patterns.append({
                    'pattern': pattern_name,
                    'points': points,
                    'ratios': ratios,
                    'completion_time': points[-1]['index'],
                    'completion_price': points[-1]['price']
                })

        return patterns

    def _validate_pattern_structure(self, points, ratios):
        """Validate if points form a valid harmonic pattern"""
        try:
            # Calculate ratios between points
            xa = abs(points[1]['price'] - points[0]['price'])
            ab = abs(points[2]['price'] - points[1]['price'])
            bc = abs(points[3]['price'] - points[2]['price'])
            cd = abs(points[4]['price'] - points[3]['price'])

            tolerance = 0.05  # 5% tolerance

            # Check each ratio
            for ratio_name, expected_ratio in ratios.items():
                if ratio_name == 'XA':
                    actual_ratio = ab / xa if xa != 0 else 0
                elif ratio_name == 'AB':
                    actual_ratio = bc / ab if ab != 0 else 0
                elif ratio_name == 'BC':
                    actual_ratio = cd / bc if bc != 0 else 0
                elif ratio_name == 'CD':
                    actual_ratio = cd / xa if xa != 0 else 0
                else:
                    continue

                if abs(actual_ratio - expected_ratio) > tolerance:
                    return False

            return True

        except:
            return False

class SMCAnalyzer:
    """Smart Money Concepts Analysis with Enhanced FVG Signal Detection"""

    # --- Updated: SMCAnalyzer.__init__ ---
    def __init__(self, logger_instance=None):
        self.structure_levels = []
        self.liquidity_zones = []
        self.order_blocks = []
        self.fair_value_gaps = []
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)

    # --- Updated: SMCAnalyzer.analyze_smc to call _analyze_fvg_signals ---
    def analyze_smc(self, df: pd.DataFrame) -> Dict:
        """Comprehensive SMC analysis"""
        results = {}

        try:
            # Market structure
            results['market_structure'] = self._analyze_market_structure(df)

            # Liquidity zones
            results['liquidity_zones'] = self._identify_liquidity_zones(df)

            # Order blocks
            results['order_blocks'] = self._identify_order_blocks(df)

            # Fair value gaps
            results['fair_value_gaps'] = self._identify_fair_value_gaps(df)

            # NEW: Analyze FVG signals
            results['fvg_signals'] = self._analyze_fvg_signals(df)

            # Breaker blocks
            results['breaker_blocks'] = self._identify_breaker_blocks(df)

            # Mitigation blocks
            results['mitigation_blocks'] = self._identify_mitigation_blocks(df)

            # Displacement analysis
            results['displacement'] = self._analyze_displacement(df)

            # Inducement analysis
            results['inducement'] = self._analyze_inducement(df)

        except Exception as e:
            self.logger.warning(f"Error in SMC analysis: {e}")

        return results

    # --- New: SMCAnalyzer._analyze_fvg_signals ---
    def _analyze_fvg_signals(self, df: pd.DataFrame) -> List[Dict]:
        """
        Analyzes Fair Value Gaps (FVGs) to identify potential high-probability trading signals.
        A signal is generated if an FVG is detected shortly after a displacement event,
        which aligns with the Smart Money Concepts idea of strong market intention
        after liquidity sweeps.
        """
        fvg_signals = []
        fair_value_gaps = self._identify_fair_value_gaps(df)
        # Re-use existing displacement analysis for context
        displacement_events = self._analyze_displacement(df)

        displacement_indices = {d['index'] for d in displacement_events}

        for fvg in fair_value_gaps:
            fvg_idx = fvg['index']
            # Check a small window (e.g., 3 bars) before the FVG for a preceding displacement
            window = 3
            is_after_displacement = False
            for i in range(max(0, fvg_idx - window), fvg_idx + 1):
                if i in displacement_indices:
                    is_after_displacement = True
                    break

            if is_after_displacement:
                fvg_signals.append({
                    'type': fvg['type'],
                    'index': fvg_idx,
                    'price_range': {'top': fvg['top'], 'bottom': fvg['bottom']},
                    'size': fvg['size'],
                    'signal_strength': 'high_probability_setup',
                    'description': (f"Major {fvg['type'].replace('_', ' ')} detected around displacement "
                                    f"at index {fvg_idx}. This often signals strong momentum "
                                    f"and potential trend continuation or reversal.")
                })
                # Optionally, annotate the original FVG with its signal status
                if 'signal' not in fvg:  # Avoid overwriting if multiple signal checks are added
                    fvg['signal'] = fvg_signals[-1]['signal_strength']

        return fvg_signals

    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """Analyze market structure"""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(2, len(high) - 2):
            if high[i] > high[i-1] and high[i] > high[i+1] and                high[i] > high[i-2] and high[i] > high[i+2]:
                swing_highs.append({'index': i, 'price': high[i]})

            if low[i] < low[i-1] and low[i] < low[i+1] and                low[i] < low[i-2] and low[i] < low[i+2]:
                swing_lows.append({'index': i, 'price': low[i]})

        # Determine trend
        trend = self._determine_trend(swing_highs, swing_lows)

        return {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'trend': trend,
            'structure_breaks': self._find_structure_breaks(swing_highs, swing_lows)
        }

    def _identify_liquidity_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Identify liquidity zones"""
        zones = []

        try:
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

            # Equal highs/lows with high volume
            for i in range(1, len(high) - 1):
                # Check for equal highs
                if abs(high[i] - high[i-1]) < (high[i] * 0.001) and volume[i] > np.mean(volume):
                    zones.append({
                        'type': 'liquidity_high',
                        'price': high[i],
                        'index': i,
                        'strength': volume[i] / np.mean(volume)
                    })

                # Check for equal lows
                if abs(low[i] - low[i-1]) < (low[i] * 0.001) and volume[i] > np.mean(volume):
                    zones.append({
                        'type': 'liquidity_low',
                        'price': low[i],
                        'index': i,
                        'strength': volume[i] / np.mean(volume)
                    })

        except Exception as e:
            self.logger.warning(f"Error identifying liquidity zones: {e}")

        return zones

    def _identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify order blocks"""
        order_blocks = []

        try:
            open_prices = df['open'].values
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            for i in range(1, len(df) - 1):
                # Bullish order block
                if close[i] > open_prices[i] and close[i+1] > high[i]:
                    order_blocks.append({
                        'type': 'bullish_ob',
                        'top': high[i],
                        'bottom': open_prices[i],
                        'index': i,
                        'strength': (close[i] - open_prices[i]) / open_prices[i]
                    })

                # Bearish order block
                if close[i] < open_prices[i] and close[i+1] < low[i]:
                    order_blocks.append({
                        'type': 'bearish_ob',
                        'top': open_prices[i],
                        'bottom': low[i],
                        'index': i,
                        'strength': (open_prices[i] - close[i]) / open_prices[i]
                    })

        except Exception as e:
            self.logger.warning(f"Error identifying order blocks: {e}")

        return order_blocks

    def _identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify fair value gaps"""
        gaps = []

        try:
            high = df['high'].values
            low = df['low'].values

            for i in range(2, len(df)):
                # Bullish FVG
                if low[i] > high[i-2]:
                    gaps.append({
                        'type': 'bullish_fvg',
                        'top': low[i],
                        'bottom': high[i-2],
                        'index': i,
                        'size': low[i] - high[i-2]
                    })

                # Bearish FVG
                if high[i] < low[i-2]:
                    gaps.append({
                        'type': 'bearish_fvg',
                        'top': low[i-2],
                        'bottom': high[i],
                        'index': i,
                        'size': low[i-2] - high[i]
                    })

        except Exception as e:
            self.logger.warning(f"Error identifying fair value gaps: {e}")

        return gaps

    def _identify_breaker_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify breaker blocks"""
        breakers = []

        try:
            # Implementation of breaker block identification
            order_blocks = self._identify_order_blocks(df)
            close = df['close'].values

            for ob in order_blocks:
                # Check if order block was broken
                for i in range(ob['index'] + 1, len(close)):
                    if ob['type'] == 'bullish_ob' and close[i] < ob['bottom']:
                        breakers.append({
                            'type': 'bearish_breaker',
                            'original_ob': ob,
                            'break_index': i,
                            'break_price': close[i]
                        })
                        break
                    elif ob['type'] == 'bearish_ob' and close[i] > ob['top']:
                        breakers.append({
                            'type': 'bullish_breaker',
                            'original_ob': ob,
                            'break_index': i,
                            'break_price': close[i]
                        })
                        break

        except Exception as e:
            self.logger.warning(f"Error identifying breaker blocks: {e}")

        return breakers

    def _identify_mitigation_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify mitigation blocks"""
        mitigations = []

        try:
            order_blocks = self._identify_order_blocks(df)
            close = df['close'].values

            for ob in order_blocks:
                # Check for mitigation (price returning to order block)
                for i in range(ob['index'] + 1, len(close)):
                    if ob['type'] == 'bullish_ob':
                        if ob['bottom'] <= close[i] <= ob['top']:
                            mitigations.append({
                                'type': 'bullish_mitigation',
                                'original_ob': ob,
                                'mitigation_index': i,
                                'mitigation_price': close[i]
                            })
                            break
                    elif ob['type'] == 'bearish_ob':
                        if ob['bottom'] <= close[i] <= ob['top']:
                            mitigations.append({
                                'type': 'bearish_mitigation',
                                'original_ob': ob,
                                'mitigation_index': i,
                                'mitigation_price': close[i]
                            })
                            break

        except Exception as e:
            self.logger.warning(f"Error identifying mitigation blocks: {e}")

        return mitigations

    def _analyze_displacement(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze displacement moves"""
        displacements = []

        try:
            close = df['close'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

            # Calculate price changes and volume
            price_changes = np.diff(close) / close[:-1]
            avg_change = np.mean(np.abs(price_changes))
            avg_volume = np.mean(volume)

            for i in range(1, len(price_changes)):
                # Significant price movement with volume
                if abs(price_changes[i]) > 2 * avg_change and volume[i] > 1.5 * avg_volume:
                    displacements.append({
                        'index': i,
                        'direction': 'bullish' if price_changes[i] > 0 else 'bearish',
                        'magnitude': abs(price_changes[i]),
                        'volume_ratio': volume[i] / avg_volume,
                        'price_change': price_changes[i]
                    })

        except Exception as e:
            self.logger.warning(f"Error analyzing displacement: {e}")

        return displacements

    def _analyze_inducement(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze inducement patterns"""
        inducements = []

        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            for i in range(2, len(df) - 2):
                # Bullish inducement (fake breakout to downside)
                if low[i] < min(low[i-2:i]) and close[i] > low[i] and close[i+1] > close[i]:
                    inducements.append({
                        'type': 'bullish_inducement',
                        'index': i,
                        'low': low[i],
                        'recovery': close[i+1] - low[i]
                    })

                # Bearish inducement (fake breakout to upside)
                if high[i] > max(high[i-2:i]) and close[i] < high[i] and close[i+1] < close[i]:
                    inducements.append({
                        'type': 'bearish_inducement',
                        'index': i,
                        'high': high[i],
                        'decline': high[i] - close[i+1]
                    })

        except Exception as e:
            self.logger.warning(f"Error analyzing inducement: {e}")

        return inducements

    def _determine_trend(self, swing_highs: List[Dict], swing_lows: List[Dict]) -> str:
        """Determine market trend"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return 'sideways'

        # Higher highs and higher lows = uptrend
        recent_highs = sorted(swing_highs, key=lambda x: x['index'])[-2:]
        recent_lows = sorted(swing_lows, key=lambda x: x['index'])[-2:]

        if (recent_highs[1]['price'] > recent_highs[0]['price'] and 
            recent_lows[1]['price'] > recent_lows[0]['price']):
            return 'uptrend'
        elif (recent_highs[1]['price'] < recent_highs[0]['price'] and 
              recent_lows[1]['price'] < recent_lows[0]['price']):
            return 'downtrend'
        else:
            return 'sideways'

    def _find_structure_breaks(self, swing_highs: List[Dict], swing_lows: List[Dict]) -> List[Dict]:
        """Find market structure breaks"""
        breaks = []
        # Implementation of structure break detection
        # This would identify when price breaks through significant swing levels
        return breaks

class WyckoffAnalyzer:
    """Micro Wyckoff Analysis"""

    # --- Updated: WyckoffAnalyzer.__init__ ---
    def __init__(self, logger_instance=None):
        self.phases = ['accumulation', 'markup', 'distribution', 'markdown']
        self.events = ['PS', 'SC', 'AR', 'ST', 'BC', 'LPS', 'SOS', 'LPSY', 'UTAD', 'LPSY2']
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)

    def analyze_wyckoff(self, df: pd.DataFrame) -> Dict:
        """Comprehensive Wyckoff analysis"""
        results = {}

        try:
            # Identify Wyckoff phases
            results['phases'] = self._identify_phases(df)

            # Identify key events
            results['events'] = self._identify_events(df)

            # Volume analysis
            results['volume_analysis'] = self._analyze_volume_patterns(df)

            # Effort vs Result
            results['effort_vs_result'] = self._analyze_effort_vs_result(df)

            # Supply and Demand
            results['supply_demand'] = self._analyze_supply_demand(df)

        except Exception as e:
            self.logger.warning(f"Error in Wyckoff analysis: {e}")

        return results

    def _identify_phases(self, df: pd.DataFrame) -> List[Dict]:
        """
        **Stable Wyckoff phase detector**
        • Pre‑computes 20‑bar volatility & volume means once  
        • No nested rolling inside the main loop  
        • Hard‑cap of 1 000 detected segments to avoid runaway loops
        """
        phases: List[Dict] = []
        if len(df) < 60 or 'close' not in df.columns:
            return phases

        close   = df['close'].to_numpy()
        volume  = df.get('volume', pd.Series(np.ones(len(df)))).to_numpy()

        # one‑time rolling calculations
        vol_20  = pd.Series(close).rolling(20).std().fillna(method='bfill').to_numpy()
        vol_50m = pd.Series(vol_20).rolling(30).mean().fillna(method='bfill').to_numpy()  # mean of the volatility
        volu_20 = pd.Series(volume).rolling(20).mean().fillna(method='bfill').to_numpy()

        for i in range(50, len(df) - 10):
            try:
                # ── Accumulation: quiet price, loud tape ────
                if vol_20[i] < 0.75 * vol_50m[i] and volume[i] > 1.25 * volu_20[i]:
                    phases.append(dict(phase='accumulation',
                                       start=i-10, end=i+10,
                                       strength=volume[i] / volu_20[i]))

                # ── Mark‑up: volatility + upward momentum + volume ────
                elif (vol_20[i] > 1.25 * vol_50m[i]
                      and close[i] > 1.01 * close[i-5]
                      and volume[i] > volu_20[i]):
                    phases.append(dict(phase='markup',
                                       start=i-5, end=i+5,
                                       strength=(close[i]-close[i-5])/close[i-5]))

                # safety valve
                if len(phases) > 1000:
                    self.logger.warning("Wyckoff phase detector stopped early (1000+ phases).")
                    break
            except Exception as e:
                self.logger.debug("Wyckoff phase calc issue @%d: %s", i, e)

        return phases

    def _identify_events(self, df: pd.DataFrame) -> List[Dict]:
        """Identify Wyckoff events"""
        events = []

        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

            # Preliminary Support (PS) - first sign of buying interest
            for i in range(10, len(df) - 10):
                if (close[i] < close[i-5] and volume[i] > np.mean(volume[i-10:i]) and
                    close[i+1] > close[i]):
                    events.append({
                        'event': 'PS',
                        'index': i,
                        'price': close[i],
                        'volume': volume[i],
                        'description': 'Preliminary Support'
                    })

            # Selling Climax (SC) - panic selling
            for i in range(10, len(df) - 10):
                if (volume[i] > 2 * np.mean(volume[i-10:i]) and
                    close[i] < close[i-1] and
                    close[i+1] > close[i]):
                    events.append({
                        'event': 'SC',
                        'index': i,
                        'price': close[i],
                        'volume': volume[i],
                        'description': 'Selling Climax'
                    })

        except Exception as e:
            self.logger.warning(f"Error identifying Wyckoff events: {e}")

        return events

    def _analyze_volume_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze volume patterns"""
        analysis = {}

        try:
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))
            close = df['close'].values

            # Volume trend analysis
            volume_trend = np.polyfit(range(len(volume)), volume, 1)[0]

            # Volume divergence
            price_trend = np.polyfit(range(len(close)), close, 1)[0]

            analysis = {
                'volume_trend': volume_trend,
                'price_trend': price_trend,
                'divergence': (price_trend > 0 and volume_trend < 0) or (price_trend < 0 and volume_trend > 0),
                'avg_volume': np.mean(volume),
                'volume_spikes': np.where(volume > 2 * np.mean(volume))[0].tolist()
            }

        except Exception as e:
            self.logger.warning(f"Error analyzing volume patterns: {e}")

        return analysis

    def _analyze_effort_vs_result(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze effort vs result"""
        analysis = []

        try:
            close = df['close'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

            for i in range(1, len(df)):
                price_change = abs(close[i] - close[i-1]) / close[i-1]
                volume_effort = volume[i] / np.mean(volume)

                if volume_effort > 1.5:  # High volume effort
                    if price_change < 0.001:  # Low price result
                        analysis.append({
                            'index': i,
                            'type': 'high_effort_low_result',
                            'effort': volume_effort,
                            'result': price_change,
                            'interpretation': 'Potential accumulation/distribution'
                        })
                    elif price_change > 0.01:  # High price result
                        analysis.append({
                            'index': i,
                            'type': 'high_effort_high_result',
                            'effort': volume_effort,
                            'result': price_change,
                            'interpretation': 'Strong move with support'
                        })

        except Exception as e:
            self.logger.warning(f"Error analyzing effort vs result: {e}")

        return analysis

    def _analyze_supply_demand(self, df: pd.DataFrame) -> Dict:
        """Analyze supply and demand"""
        analysis = {}

        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(df))

            # Supply zones (resistance areas with high volume)
            supply_zones = []
            demand_zones = []

            for i in range(10, len(df) - 10):
                # Supply zone
                if (high[i] == max(high[i-5:i+5]) and
                    volume[i] > np.mean(volume[i-10:i+10])):
                    supply_zones.append({
                        'price': high[i],
                        'index': i,
                        'strength': volume[i] / np.mean(volume[i-10:i+10])
                    })

                # Demand zone
                if (low[i] == min(low[i-5:i+5]) and
                    volume[i] > np.mean(volume[i-10:i+10])):
                    demand_zones.append({
                        'price': low[i],
                        'index': i,
                        'strength': volume[i] / np.mean(volume[i-10:i+10])
                    })

            analysis = {
                'supply_zones': supply_zones,
                'demand_zones': demand_zones,
                'current_bias': self._determine_supply_demand_bias(close, volume)
            }

        except Exception as e:
            self.logger.warning(f"Error analyzing supply/demand: {e}")

        return analysis

    def _determine_supply_demand_bias(self, close, volume):
        """Determine current supply/demand bias"""
        try:
            recent_close = close[-10:]
            recent_volume = volume[-10:]

            # Up moves vs down moves with volume
            up_volume = sum(recent_volume[i] for i in range(1, len(recent_close)) if recent_close[i] > recent_close[i-1])
            down_volume = sum(recent_volume[i] for i in range(1, len(recent_close)) if recent_close[i] < recent_close[i-1])

            if up_volume > down_volume * 1.2:
                return 'demand_dominant'
            elif down_volume > up_volume * 1.2:
                return 'supply_dominant'
            else:
                return 'balanced'
        except:
            return 'unknown'

class TickDataAnalyzer:
    """Advanced tick data analysis"""

    # --- Updated: TickDataAnalyzer.__init__ ---
    def __init__(self, config: AnalysisConfig, logger_instance=None):
        self.config = config
        self.tick_limit = config.tick_bars_limit
        self.logger = logger_instance if logger_instance else logging.getLogger(__name__)

    def analyze_tick_data(self, df: pd.DataFrame) -> Dict:
        """Comprehensive tick data analysis"""
        results = {}

        try:
            # Limit tick data if specified
            if len(df) > self.tick_limit:
                df = df.tail(self.tick_limit)
                self.logger.info(f"Limited tick data to last {self.tick_limit} ticks")

            # Microstructure analysis
            results['microstructure'] = self._analyze_microstructure(df)

            # Spread analysis
            results['spread_analysis'] = self._analyze_spreads(df)

            # Volume analysis
            results['volume_analysis'] = self._analyze_tick_volume(df)

            # Market manipulation detection
            results['manipulation'] = self._detect_manipulation(df)

            # Liquidity analysis
            results['liquidity'] = self._analyze_liquidity(df)

            # Order flow
            results['order_flow'] = self._analyze_order_flow(df)

        except Exception as e:
            self.logger.warning(f"Error in tick data analysis: {e}")

        return results

    # ... [rest of TickDataAnalyzer methods remain the same] ...

class UltimateDataProcessor:
    """Ultimate data processing engine with all features enabled by default"""

    # --- Updated: UltimateDataProcessor.__init__ ---
    def __init__(self, config: AnalysisConfig):
        self.config = config
        # Existing logger definition at global scope. We'll use that.
        global logger  # Ensure access to the global logger instance
        self.logger = logger
        self.indicator_engine = UltimateIndicatorEngine(self.logger)  # Passed logger
        self.harmonic_detector = HarmonicPatternDetector(self.logger)  # Passed logger
        self.smc_analyzer = SMCAnalyzer(self.logger)  # Passed logger
        self.wyckoff_analyzer = WyckoffAnalyzer(self.logger)  # Passed logger
        self.tick_analyzer = TickDataAnalyzer(config, self.logger)  # Passed logger

    # --- New: UltimateDataProcessor._generate_analysis_metadata ---
    def _generate_analysis_metadata(self, df: pd.DataFrame, all_analysis_results: Dict) -> Dict:
        """
        Generates comprehensive metadata for the analysis, including column descriptions,
        feature theories, and details about detected signals. This metadata provides
        context and a deeper understanding of the generated data.
        """
        metadata = {
            "analysis_description": "Comprehensive market microstructure and trading strategy analysis, focusing on key concepts like Smart Money Concepts (SMC) and session-specific behaviors.",
            "columns_info": {},
            "features_theory": {},
            "detected_signals_summary": {}
        }

        # 1. Column Information (for columns added or specifically referenced)
        # This automatically includes new columns like 'is_london_killzone'
        if "session" in df.columns:
            metadata["columns_info"]["session"] = {
                "description": "Trading session based on UTC hour: 'AS' (Asian), 'EU' (European/London), 'US' (US/New York).",
                "type": "categorical string",
                "units": "N/A",
                "how_calculated": "Mapped from UTC hour: AS (0-6, 22-23), EU (7-12), US (13-21).",
                "commentary": "Market behavior often changes significantly across different trading sessions due to varying participant liquidity and volume."
            }
        if "is_london_killzone" in df.columns:
            metadata["columns_info"]["is_london_killzone"] = {
                "description": "Boolean flag indicating if the current bar is within the London Kill Zone.",
                "type": "boolean",
                "units": "N/A",
                "how_calculated": "True if UTC hour is between 7:00 (inclusive) and 13:00 (exclusive). This aligns with the London session beginning and its specific characteristics.",
                "commentary": "The London Kill Zone is identified as an important time for trading due to significant liquidity injection, new market participants, and a tendency for daily highs/lows to form within this period. It is a critical timing aspect for many strategies."
            }
        if "atr_14" in df.columns:  # Existing indicator, but good to document fully
            metadata["columns_info"]["atr_14"] = {
                "description": "Average True Range (ATR) over 14 periods.",
                "type": "float",
                "units": "price units",
                "how_calculated": "Calculated using TA-Lib's ATR function over 14 periods. ATR measures market volatility by calculating the average of true ranges over a specified period.",
                "commentary": "A higher ATR indicates higher volatility. Spikes in ATR (e.g., atr_value > 2 * mean(ATR)) can signal significant market events, potential reversals, or increased trading opportunities."
            }

        # 2. Features Theory & Commentary
        metadata["features_theory"]["smart_money_concepts"] = {
            "description": "Smart Money Concepts (SMC) analysis focuses on identifying footprints of institutional traders (the 'smart money') by analyzing market structure, liquidity, order blocks, and fair value gaps. The goal is to trade in alignment with large institutional flows rather than against them.",
            "sub_features": {
                "fair_value_gaps": {
                    "description": "Fair Value Gaps (FVG), also known as inefficiencies or imbalances, represent areas in price delivery where price has moved rapidly in one direction without sufficient opposing market participation, leaving a 'gap' in the candles. These gaps are often seen as 'magnets' or areas where price may eventually return to be 'filled' or 'mitigated'.",
                    "calculation_method": "Identified when the low of candle 'i' is greater than the high of candle 'i-2' (bullish FVG), or when the high of candle 'i' is less than the low of candle 'i-2' (bearish FVG).",
                    "nested_structure": "{'type': 'bullish_fvg'/'bearish_fvg', 'top': price, 'bottom': price, 'index': bar_index, 'size': gap_size, 'signal': optional_signal_strength}"
                },
                "displacement": {
                    "description": "Displacement is a sharp, aggressive, and often high-volume move that breaks market structure, typically leaving behind a fair value gap. It signifies strong institutional conviction and a potential, decisive shift in trend or momentum. It's metaphorically described as 'like a big elephant jumping into a pool and then the water splashes'.",
                    "calculation_method": "Detected by significant price movement (e.g., absolute percentage change greater than 2 times the average change) coupled with unusually high volume (e.g., volume greater than 1.5 times the average volume) over a short period."
                },
                "liquidity_sweeps": {
                    "description": "Liquidity sweeps (or liquidity grabs/hunts) occur when price moves beyond a significant high or low (where stop-losses, buy stops, or sell stops are clustered), 'sweeps' or 'grabs' that accumulated liquidity, and then often reverses sharply. These are crucial for identifying potential high-probability trading opportunities as they can indicate exhaustion of a move or the start of a new trend. They are often associated with 'fake outs' or 'failed breakouts'.",
                    "commentary": "Recognizing liquidity sweeps is fundamental to identifying market manipulation and trading against the majority, aligning with institutional flow."
                },
                "order_blocks": {
                    "description": "Order Blocks are specific candles or series of candles where large institutional orders were likely placed, leading to a significant price move away from that area. They are considered areas of concentrated supply or demand that price may revisit to mitigate remaining orders.",
                    "calculation_method": "For a bullish order block, it's typically the last down candle before a strong move up. For a bearish order block, it's the last up candle before a strong move down. Specific rules involve checking subsequent candle closes relative to the order block's high/low."
                }
            }
        }
        metadata["features_theory"]["london_kill_zone_strategy"] = {
            "description": "The London Kill Zone trading strategy is a timing-based approach focusing on exploiting the unique characteristics of the London trading session. It involves observing liquidity dynamics and market structure shifts (like displacement and change of character) within this specific time window for high-probability setups.",
            "key_characteristics": [
                "**High Liquidity Injection**: Significant liquidity enters the market at the start of the London session due to active trading of major currencies (Euro, Pound, Frank) and Gold.",
                "**New Trend Formation**: New participants often join, causing market movements distinct from the Asian session and frequently leading to the formation of new trends.",
                "**Daily Extremes**: The high and low of the day are often established within this trading session.",
                "**Common Patterns**: Strategies often look for liquidity sweeps beyond the Asian session's high/low, followed by either continuation of a higher timeframe trend or a complete shift in market direction.",
                "**Midas Model Integration**: Specific scalping models like the 'Midas Model' (for Gold) leverage precise timing within the London and New York sessions, looking for liquidity sweeps and market structure shifts (displacement with FVGs) on lower timeframes."
            ]
        }

        # 3. Detected Signals Summary
        # Extract FVG signals from the results dict
        if 'smc_analysis' in all_analysis_results and 'fvg_signals' in all_analysis_results['smc_analysis']:
            fvg_signals = all_analysis_results['smc_analysis']['fvg_signals']
            if fvg_signals:
                metadata["detected_signals_summary"]["fvg_signals_after_displacement"] = {
                    "count": len(fvg_signals),
                    "examples": fvg_signals[:min(3, len(fvg_signals))],  # Show up to 3 examples
                    "description": "Fair Value Gaps identified as strong trading signals due to their occurrence after detected displacement, indicative of a significant institutional move."
                }

        # Example for other signals (e.g., ATR spikes) - this would need separate detection logic in the future
        if 'indicators' in all_analysis_results and 'ATR_14' in all_analysis_results['indicators']:
            atr_values = all_analysis_results['indicators']['ATR_14']
            if len(atr_values) > 14:  # Ensure enough data for meaningful average
                mean_atr = np.nanmean(atr_values)
                # Define an ATR spike as values significantly above the average
                atr_spike_threshold = mean_atr * 2.0  # Arbitrary threshold for example
                atr_spikes_detected = []
                for i, atr_val in enumerate(atr_values):
                    if not np.isnan(atr_val) and atr_val > atr_spike_threshold:
                        # Check for a "spike" more dynamically, e.g. relative to recent values
                        # For simplicity, we just check against mean for summary
                        atr_spikes_detected.append({'index': i, 'value': float(atr_val), 'threshold': float(atr_spike_threshold)})

                if atr_spikes_detected:
                    metadata["detected_signals_summary"]["atr_spikes"] = {
                        "count": len(atr_spikes_detected),
                        "description": f"Periods of significant volatility (ATR_14 > {atr_spike_threshold:.2f}), potentially signaling major market events or turning points."
                    }

        # Add timestamp for when this metadata was generated
        metadata["generation_timestamp_utc"] = datetime.utcnow().isoformat() + "Z"

        return metadata

    # --- Updated: UltimateDataProcessor.process_file ---
    async def process_file(self, file_path: str) -> Dict:
        """Process a single file with maximum analysis"""
        self.logger.info(f"Processing file: {file_path}")
        symbol = extract_symbol_from_filename(Path(file_path).name)
        try:
            self.logger.info("STARTING: load data")
            # Load data
            df = await self._load_data(file_path)
            self.logger.info("FINISHED: load data")

            if df is None or df.empty:
                self.logger.error(f"Failed to load data from {file_path}")
                return {'error': 'Failed to load data', 'file_path': file_path}

            self.logger.info("STARTING: apply limits")
            # Apply limits
            df = self._apply_limits(df, file_path)
            self.logger.info("FINISHED: apply limits")

            # Initialize results
            results = {
                'file_path': file_path,
                'total_bars': len(df),
                'timeframe': self._detect_timeframe(file_path),
                'currency_pair': self._detect_currency_pair(file_path),
                'analysis_timestamp': datetime.now().isoformat()
            }

            self.logger.info("STARTING: basic stats")
            # Basic statistics
            results['basic_stats'] = self._calculate_basic_stats(df)
            self.logger.info("FINISHED: basic stats")

            # Skip indicators and patterns if essential OHLC columns missing
            required_ohlc = ['open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required_ohlc):
                self.logger.warning("Skipping indicators/patterns: missing OHLC columns")
                results['indicators'] = {}
                results['harmonic_patterns'] = []
                results['smc_analysis'] = {}
                results['wyckoff_analysis'] = {}
            else:
                # Technical indicators (ALWAYS ENABLED)
                results['indicators'] = self.indicator_engine.calculate_all_indicators(df)
                try:
                    for col_name, values in results['indicators'].items():
                        if len(values) == len(df):
                            df[col_name] = values
                except Exception as e:
                    self.logger.warning(f"Failed to append indicator columns: {e}")
                self.logger.info("FINISHED: indicators")

                self.logger.info("STARTING: harmonic patterns")
                results['harmonic_patterns'] = self.harmonic_detector.detect_patterns(df)
                self.logger.info("FINISHED: harmonic patterns")

                self.logger.info("STARTING: SMC analysis")
                results['smc_analysis'] = self.smc_analyzer.analyze_smc(df)
                self.logger.info("FINISHED: SMC analysis")

                self.logger.info("STARTING: Wyckoff analysis")
                results['wyckoff_analysis'] = self.wyckoff_analyzer.analyze_wyckoff(df)
                self.logger.info("FINISHED: Wyckoff analysis")

            # Tick data analysis (ALWAYS ENABLED if tick data)
            if self._is_tick_data(file_path):
                self.logger.info("STARTING: tick analysis")
                results['tick_analysis'] = self.tick_analyzer.analyze_tick_data(df)
                self.logger.info("FINISHED: tick analysis")

            self.logger.info("STARTING: advanced analytics")
            # Advanced analytics (ALWAYS ENABLED)
            results['advanced_analytics'] = await self._perform_advanced_analytics(df)
            self.logger.info("FINISHED: advanced analytics")

            self.logger.info("STARTING: risk metrics")
            # Risk metrics (ALWAYS ENABLED)
            results['risk_metrics'] = self._calculate_risk_metrics(df)
            self.logger.info("FINISHED: risk metrics")

            self.logger.info("STARTING: ML features")
            # Machine learning features (ALWAYS ENABLED)
            results['ml_features'] = await self._extract_ml_features(df)
            self.logger.info("FINISHED: ML features")

            # --- NEW: Generate and attach comprehensive analysis metadata ---
            # Call after all analysis results are populated in 'results'
            results['analysis_metadata'] = self._generate_analysis_metadata(df, results)

            # Save per-symbol comprehensive JSON and parquet output
            try:
                # Use regex-based extractor for symbol
                tf = results.get('timeframe', 'unknown')
                base_output_dir = self.config.output_dir if hasattr(self.config, 'output_dir') else './out'
                parquet_root = os.path.join(base_output_dir, 'parquet')
                json_root = os.path.join(base_output_dir, 'json')

                # Prepare full_results for multiple timeframes (resample)
                full_results = {}
                full_results[tf] = df  # original timeframe with indicator columns attached

                resample_rules = {
                    '5min': '5T', '15min': '15T', '30min': '30T',
                    '1h': '1H', '4h': '4H', '1d': '1D'
                }

                for target_tf, rule in resample_rules.items():
                    try:
                        if tf != target_tf:
                            df_resampled = df.resample(rule).agg({
                                'open': 'first', 'high': 'max', 'low': 'min',
                                'close': 'last', 'volume': 'sum'
                            }).dropna()
                            # Retain all extra indicator columns via forward fill where applicable
                            for col in df.columns:
                                if col not in ['open', 'high', 'low', 'close', 'volume']:
                                    df_resampled[col] = df[col].resample(rule).ffill().dropna()
                            full_results[target_tf] = df_resampled
                    except Exception as e:
                        self.logger.warning(f"Failed to resample to {target_tf}: {e}")

                # Filtering by timeframes and limiting max candles is done here:
                data_by_timeframe = full_results
                if self.config.timeframes_parquet:
                    data_by_timeframe = {t: d for t, d in data_by_timeframe.items() if t in self.config.timeframes_parquet}
                if self.config.max_candles:
                    data_by_timeframe = {t: d.tail(self.config.max_candles) for t, d in data_by_timeframe.items()}

                # --- UPDATED CALL: Pass the generated analysis_metadata ---
                save_results_to_parquet_and_json(symbol, data_by_timeframe, parquet_root, json_root, self.config.csv_dir, analysis_metadata=results['analysis_metadata'])
                self.logger.info(f"Saved parquet and JSON for symbol: {symbol}")

            except Exception as e:
                self.logger.error(f"Error saving parquet/JSON for {symbol}: {e}")

            self.logger.info(f"Completed processing: {file_path}")
            return results

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return {'error': str(e), 'file_path': file_path}

    async def _load_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load data from CSV and JSON files"""
        try:
            if file_path.endswith('.csv'):
                # Try different separators, propagate KeyboardInterrupt
                for sep in ['\t', ',', ';']:
                    try:
                        df = pd.read_csv(file_path, sep=sep)
                        if len(df.columns) > 1:  # Successfully parsed
                            # Attempt to parse timestamp as well
                            if 'timestamp' in df.columns:
                                try:
                                    df['timestamp'] = pd.to_datetime(
                                        df['timestamp'],
                                        format='%Y.%m.%d %H:%M:%S',
                                        errors='coerce'
                                    )
                                    df.set_index('timestamp', inplace=True)
                                except Exception:
                                    # fallback: parse without format string
                                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                                    df.set_index('timestamp', inplace=True)
                            return df
                    except KeyboardInterrupt:
                        raise
                    except Exception:
                        continue
                return None

            elif file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # Convert to DataFrame based on structure
                if isinstance(data, dict) and 'data' in data:
                    return pd.DataFrame(data['data'])
                elif isinstance(data, list):
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame([data])

            elif file_path.endswith('.json.gz'):
                with gzip.open(file_path, 'rt') as f:
                    data = json.load(f)

                if isinstance(data, dict) and 'data' in data:
                    return pd.DataFrame(data['data'])
                elif isinstance(data, list):
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame([data])

        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return None

    def _apply_limits(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """Apply bar limits based on timeframe"""
        try:
            if self._is_tick_data(file_path):
                if len(df) > self.config.tick_bars_limit:
                    df = df.tail(self.config.tick_bars_limit)
                    self.logger.info(f"Limited to {self.config.tick_bars_limit} tick bars")
            else:
                timeframe = self._detect_timeframe(file_path)
                if timeframe in self.config.bar_limits:
                    limit = self.config.bar_limits[timeframe]
                    if len(df) > limit:
                        df = df.tail(limit)
                        self.logger.info(f"Limited to {limit} bars for {timeframe}")

            return df
        except:
            return df

    def _detect_timeframe(self, file_path: str) -> str:
        """Detect timeframe from filename"""
        timeframe_patterns = {
            r'(?i)tick': 'tick',
            r'(?i)m1|1min|1minute': '1min',
            r'(?i)m5|5min|5minute': '5min',
            r'(?i)m15|15min|15minute': '15min',
            r'(?i)m30|30min|30minute': '30min',
            r'(?i)h1|1h|1hour': '1h',
            r'(?i)h4|4h|4hour': '4h',
            r'(?i)d1|1d|1day|daily': '1d',
            r'(?i)w1|1w|1week|weekly': '1w',
            r'(?i)mn1|1mn|1month|monthly': '1M'
        }

        filename = Path(file_path).name.lower()
        for pattern, tf in timeframe_patterns.items():
            if re.search(pattern, filename):
                return tf

        return 'unknown'

    def _detect_currency_pair(self, file_path: str) -> str:
        """Detect currency pair from filename"""
        pair_patterns = [
            r'(?i)(EUR|GBP|USD|JPY|CHF|CAD|AUD|NZD|XAU|XAG|BTC|ETH|OIL|GAS|SPX|NAS|DJI|DAX|FTSE|NIKKEI)[A-Z]{3}',
            r'(?i)(GOLD|SILVER|CRUDE|BRENT)',
            r'(?i)(BITCOIN|ETHEREUM|LITECOIN|RIPPLE)'
        ]

        filename = Path(file_path).name
        for pattern in pair_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(0).upper()

        return 'UNKNOWN'

    def _is_tick_data(self, file_path: str) -> bool:
        """Check if file contains tick data"""
        return 'tick' in Path(file_path).name.lower()

    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict:
        """Calculate basic statistics"""
        stats = {}

        try:
            if 'close' in df.columns:
                close = df['close']
                stats.update({
                    'first_price': close.iloc[0],
                    'last_price': close.iloc[-1],
                    'high_price': close.max(),
                    'low_price': close.min(),
                    'price_change': close.iloc[-1] - close.iloc[0],
                    'price_change_pct': ((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100,
                    'volatility': close.pct_change().std() * np.sqrt(252),
                    'skewness': close.pct_change().skew(),
                    'kurtosis': close.pct_change().kurtosis()
                })

            if 'volume' in df.columns:
                volume = df['volume']
                stats.update({
                    'total_volume': volume.sum(),
                    'avg_volume': volume.mean(),
                    'volume_std': volume.std(),
                    'max_volume': volume.max(),
                    'min_volume': volume.min()
                })

            # Time-based stats
            if hasattr(df.index, 'to_pydatetime'):
                stats.update({
                    'start_time': df.index[0].isoformat(),
                    'end_time': df.index[-1].isoformat(),
                    'duration_hours': (df.index[-1] - df.index[0]).total_seconds() / 3600
                })

        except Exception as e:
            self.logger.warning(f"Error calculating basic stats: {e}")

        return stats

    async def _perform_advanced_analytics(self, df: pd.DataFrame) -> Dict:
        """Perform advanced analytics"""
        analytics = {}

        try:
            if 'close' in df.columns:
                close = df['close'].values

                self.logger.info("STARTING: fractal dimension")
                # Fractal dimension
                analytics['fractal_dimension'] = self._calculate_fractal_dimension(close)
                self.logger.info("FINISHED: fractal dimension")

                self.logger.info("STARTING: hurst exponent")
                # Hurst exponent
                analytics['hurst_exponent'] = self._calculate_hurst_exponent(close)
                self.logger.info("FINISHED: hurst exponent")

                # Approximate entropy (with check for series size)
                if len(close) > 2000:
                    self.logger.info("SKIPPING: approximate entropy (series too large: %d rows)", len(close))
                    analytics['approximate_entropy'] = np.nan
                else:
                    self.logger.info("STARTING: approximate entropy")
                    analytics['approximate_entropy'] = self._calculate_approximate_entropy(close)
                    self.logger.info("FINISHED: approximate entropy")

                self.logger.info("STARTING: DFA")
                # Detrended fluctuation analysis
                analytics['dfa_alpha'] = self._calculate_dfa(close)
                self.logger.info("FINISHED: DFA")

                self.logger.info("STARTING: efficiency ratio")
                # Market efficiency ratio
                analytics['efficiency_ratio'] = self._calculate_efficiency_ratio(close)
                self.logger.info("FINISHED: efficiency ratio")

                self.logger.info("STARTING: trend strength")
                # Trend strength
                analytics['trend_strength'] = self._calculate_trend_strength(close)
                self.logger.info("FINISHED: trend strength")

                self.logger.info("STARTING: support/resistance")
                # Support and resistance levels
                analytics['support_resistance'] = self._find_support_resistance(df)
                self.logger.info("FINISHED: support/resistance")

                self.logger.info("STARTING: fibonacci levels")
                # Fibonacci levels
                analytics['fibonacci_levels'] = self._calculate_fibonacci_levels(close)
                self.logger.info("FINISHED: fibonacci levels")

            # Augmented Dickey-Fuller stationarity test (ALWAYS ENABLED)
            try:
                if 'close' in df.columns:
                    analytics['adf_fuller'] = add_fuller(df['close'].values)
            except Exception as e:
                analytics['adf_fuller'] = {'error': str(e)}

        except Exception as e:
            self.logger.warning(f"Error in advanced analytics: {e}")

        return analytics

    def _find_support_resistance(self, df: pd.DataFrame) -> dict:
        """Simple support/resistance finder for close prices."""
        if 'close' not in df.columns:
            return {}
        close = df['close'].values
        support = float(np.min(close))
        resistance = float(np.max(close))
        return {'support': support, 'resistance': resistance}

    def _calculate_fibonacci_levels(self, close: np.ndarray) -> Dict:
        """Calculate Fibonacci retracement levels"""
        try:
            high = np.max(close)
            low = np.min(close)
            diff = high - low
            
            levels = {
                '0.0': high,
                '23.6': high - 0.236 * diff,
                '38.2': high - 0.382 * diff,
                '50.0': high - 0.5 * diff,
                '61.8': high - 0.618 * diff,
                '78.6': high - 0.786 * diff,
                '100.0': low
            }
            return levels
        except:
            return {}

    async def _extract_ml_features(self, df: pd.DataFrame) -> dict:
        """Stub ML feature extractor. Expand as needed."""
        # For now, return an empty dict to avoid errors.
        return {}

    def _calculate_risk_metrics(self, df: pd.DataFrame) -> dict:
        """Stub risk metrics calculation. Expand as needed."""
        try:
            if 'close' not in df.columns:
                return {}
            close = df['close'].values
            returns = np.diff(close) / close[:-1]
            return {
                'std_dev': float(np.std(returns)),
                'max_drawdown': float(np.min((close - np.maximum.accumulate(close)) / np.maximum.accumulate(close))),
                'value_at_risk_95': float(np.percentile(returns, 5))
            }
        except Exception:
            return {}

    def _calculate_fractal_dimension(self, data: np.ndarray) -> float:
        """Calculate fractal dimension using box counting method"""
        try:
            def box_count(data, r):
                n = len(data)
                boxes = np.ceil(n / r).astype(int)
                count = 0
                for i in range(boxes):
                    start = i * r
                    end = min((i + 1) * r, n)
                    if np.max(data[start:end]) - np.min(data[start:end]) > 0:
                        count += 1
                return count

            scales = np.logspace(0.5, 2, 10).astype(int)
            scales = np.unique(scales)
            counts = [box_count(data, r) for r in scales]

            # Fit line to log-log plot
            coeffs = np.polyfit(np.log(scales), np.log(counts), 1)
            return -coeffs[0]

        except:
            return np.nan

    def _calculate_hurst_exponent(self, data: np.ndarray) -> float:
        """Calculate Hurst exponent"""
        try:
            lags = range(2, min(100, len(data) // 4))
            tau = [np.var(np.diff(data, n=lag)) for lag in lags]

            # Fit line to log-log plot
            coeffs = np.polyfit(np.log(lags), np.log(tau), 1)
            return coeffs[0] / 2.0

        except:
            return np.nan

    def _calculate_approximate_entropy(self, data: np.ndarray, m: int = 2, r: float = None) -> float:
        """Calculate approximate entropy"""
        try:
            if r is None:
                r = 0.2 * np.std(data)

            def _maxdist(xi, xj, N, m):
                return max([abs(ua - va) for ua, va in zip(xi[0:m], xj[0:m])])

            def _phi(m):
                N = len(data)
                patterns = np.array([data[i:i + m] for i in range(N - m + 1)])
                C = np.zeros(N - m + 1)

                for i in range(N - m + 1):
                    template_i = patterns[i]
                    for j in range(N - m + 1):
                        if _maxdist(template_i, patterns[j], N, m) <= r:
                            C[i] += 1.0

                C = C / float(N - m + 1.0)
                phi = np.mean(np.log(C))
                return phi

            return _phi(m) - _phi(m + 1)

        except:
            return np.nan

    def _calculate_dfa(self, data: np.ndarray) -> float:
        """Calculate Detrended Fluctuation Analysis alpha"""
        try:
            # Integrate the data
            y = np.cumsum(data - np.mean(data))

            # Define scales
            scales = np.unique(np.logspace(0.5, 2.5, 20).astype(int))
            scales = scales[scales < len(data) // 4]

            F = []
            for scale in scales:
                # Divide into segments
                segments = len(y) // scale
                if segments == 0:
                    continue

                # Calculate fluctuation for each segment
                fluctuations = []
                for i in range(segments):
                    start = i * scale
                    end = (i + 1) * scale
                    segment = y[start:end]

                    # Fit polynomial trend
                    x = np.arange(len(segment))
                    coeffs = np.polyfit(x, segment, 1)
                    trend = np.polyval(coeffs, x)

                    # Calculate fluctuation
                    fluctuation = np.sqrt(np.mean((segment - trend)**2))
                    fluctuations.append(fluctuation)

                F.append(np.mean(fluctuations))

            # Fit line to log-log plot
            if len(F) > 1:
                valid_scales = scales[:len(F)]
                coeffs = np.polyfit(np.log(valid_scales), np.log(F), 1)
                return coeffs[0]

        except:
            pass

        return np.nan

    def _calculate_efficiency_ratio(self, data: np.ndarray, period: int = 20) -> float:
        """Calculate Market Efficiency Ratio"""
        try:
            if len(data) < period:
                return np.nan

            # Price change over period
            change = abs(data[-1] - data[-period])

            # Sum of absolute daily changes
            volatility = np.sum(np.abs(np.diff(data[-period:])))

            if volatility == 0:
                return 0

            return change / volatility

        except:
            return np.nan

    def _calculate_trend_strength(self, data: np.ndarray) -> float:
        """Simple trend strength measure: R^2 of linear fit."""
        try:
            if len(data) < 2:
                return np.nan
            x = np.arange(len(data))
            slope, intercept = np.polyfit(x, data, 1)
            # Compute R^2
            p = np.poly1d([slope, intercept])
            y_hat = p(x)
            ss_res = np.sum((data - y_hat)**2)
            ss_tot = np.sum((data - np.mean(data))**2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            return r2
        except Exception:
            return np.nan

# --- Updated: save_results_to_parquet_and_json ---
def save_results_to_parquet_and_json(symbol, data_by_timeframe, parquet_root='./parquet', json_root='./json', csv_root='./csv', analysis_metadata=None):
    """
    Save results to parquet, JSON, and CSV for each timeframe, now including comprehensive metadata.
    """
    import os
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq

    symbol_csv_dir = os.path.join(csv_root, symbol)
    os.makedirs(symbol_csv_dir, exist_ok=True)

    # Save to CSV (unchanged logic for CSVs themselves)
    for tf, df in data_by_timeframe.items():
        csv_file = os.path.join(symbol_csv_dir, f"{symbol}_{tf}.csv")
        if 'tickvol' in df.columns:
            df['volume'] = df['tickvol']
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={"index": "timestamp"})
        elif "timestamp" not in df.columns:
            for col in df.columns:
                if col.lower().startswith("time") or col.lower().startswith("date"):
                    df = df.rename(columns={col: "timestamp"})
                    break
        if "timestamp" in df.columns:
            cols = list(df.columns)
            cols.insert(0, cols.pop(cols.index("timestamp")))
            df = df[cols]
        df.to_csv(csv_file, index=False)

    symbol_parquet_dir = os.path.join(parquet_root, symbol)
    os.makedirs(symbol_parquet_dir, exist_ok=True)
    os.makedirs(json_root, exist_ok=True)

    comprehensive_json_output = {}

    # Save to Parquet and prepare data for comprehensive JSON
    for tf, df in data_by_timeframe.items():
        parquet_file = os.path.join(symbol_parquet_dir, f"{symbol}_{tf}.parquet")

        if 'tickvol' in df.columns:
            df['volume'] = df['tickvol']
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={"index": "timestamp"})
        elif "timestamp" not in df.columns:
            for col in df.columns:
                if col.lower().startswith("time") or col.lower().startswith("date"):
                    df = df.rename(columns={col: "timestamp"})
                    break
        if "timestamp" in df.columns:
            cols = list(df.columns)
            cols.insert(0, cols.pop(cols.index("timestamp")))
            df = df[cols]

        table = pa.Table.from_pandas(df, preserve_index=False)

        # Base metadata for Parquet footer
        meta_dict = {
            "columns": df.columns.tolist(),
            "symbol": symbol,
            "timeframe": tf
        }
        # NEW: Embed the comprehensive analysis_metadata directly into Parquet metadata
        if analysis_metadata:
            meta_dict["ncos_analysis_metadata"] = analysis_metadata

        # Ensure all metadata is string-encoded for PyArrow
        table = table.replace_schema_metadata({b"ncos_meta": json.dumps(meta_dict, default=str).encode()})
        pq.write_table(table, parquet_file, compression="snappy")

        comprehensive_json_output[tf] = df.to_dict(orient='records')

    # NEW: Add the comprehensive analysis_metadata to the main JSON output as well
    if analysis_metadata:
        comprehensive_json_output["_analysis_metadata"] = analysis_metadata

    json_file_path = os.path.join(json_root, f"{symbol}_comprehensive.json")
    with open(json_file_path, 'w') as json_file:
        # Use default=str for json.dump to handle datetime objects gracefully
        json.dump(comprehensive_json_output, json_file, indent=4, default=str)

# Main function and CLI remain the same as original
async def main():
    """Main function with ALL features enabled by default"""
    parser = argparse.ArgumentParser(description='ncOS Ultimate Microstructure Analyzer - Enhanced Edition with ZANFLOW v12 Integration')

    # Input options
    parser.add_argument('--directory', '-d', type=str, help='Directory to scan for files')
    parser.add_argument('--file', '-f', type=str, help='Single file to process')
    parser.add_argument('--pattern', '-p', type=str, default='*', help='File pattern to match (supports CSV and JSON)')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recursive directory scan')

    # Processing options
    parser.add_argument('--tick_bars', type=int, default=1500, help='Maximum number of tick bars to process (DEFAULT: 1500)')
    parser.add_argument('--timeframes', nargs='+', default=['1min', '5min', '15min', '30min', '1h', '4h', '1d'],
                        help='Timeframes to process')
    parser.add_argument('--bar_limits', type=str, help='JSON string of bar limits per timeframe')

    # Output options
    parser.add_argument('--output_dir', '-o', type=str, default='./ultimate_analysis_results', help='Output directory')
    parser.add_argument('--no_compression', action='store_true', help='Disable output compression')
    parser.add_argument('--json_dir', type=str, default='./json', help='Directory to save JSON files')
    parser.add_argument('--csv_dir', type=str, default='./csv', help='Directory to save CSV exports (mirrors Parquet structure)')
    parser.add_argument('--timeframes_parquet', type=str, default=None, help='Comma-separated list of timeframes to export (e.g., M1,M5)')
    parser.add_argument('--max_candles', type=int, default=60, help='Max number of candles to export per timeframe (default: 60)')

    args = parser.parse_args()

    # Create configuration with ALL FEATURES ENABLED BY DEFAULT
    config = AnalysisConfig(
        tick_bars_limit=args.tick_bars,
        bar_limits=json.loads(args.bar_limits) if args.bar_limits else {},
        # ALL ANALYSIS FEATURES ENABLED BY DEFAULT
        enable_all_indicators=True,
        enable_harmonic_patterns=True,
        enable_smc_analysis=True,
        enable_wyckoff_analysis=True,
        process_tick_data=True,
        enable_ml_predictions=True,
        enable_risk_metrics=True,
        save_all_plots=True,
        compress_output=not args.no_compression,
        process_csv_files=True,
        process_json_files=True
    )
    config.json_dir = args.json_dir
    config.csv_dir = args.csv_dir
    config.timeframes_parquet = (
        [x.strip() for x in args.timeframes_parquet.split(',')]
        if args.timeframes_parquet else None
    )
    config.max_candles = args.max_candles

    # Create processor
    processor = UltimateDataProcessor(config)

    # Get files to process (CSV and JSON by default)
    files_to_process = []

    if args.file:
        files_to_process.append(args.file)
    elif args.directory:
        directory = Path(args.directory)
        if directory.exists():
            # Process both CSV and JSON files by default
            if args.recursive:
                files_to_process.extend(directory.rglob('*.csv'))
                files_to_process.extend(directory.rglob('*.json'))
            else:
                files_to_process.extend(directory.glob('*.csv'))
                files_to_process.extend(directory.glob('*.json'))

    if not files_to_process:
        logger.error("No CSV or JSON files found to process")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"🚀 ENHANCED ULTIMATE ANALYSIS STARTING - Processing {len(files_to_process)} files with ZANFLOW v12 Integration")
    logger.info(f"📊 Tick bars limit: {args.tick_bars}")
    logger.info(f"📁 Processing: CSV and JSON files")
    logger.info(f"💎 All indicators, SMC with FVG signals, Wyckoff, London Kill Zone, ML, Risk metrics ENABLED")

    # Process files
    results = {}
    tasks = [asyncio.create_task(processor.process_file(str(fp))) for fp in files_to_process]

    try:
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results[result.get("file_path", "unknown")] = result
                logger.info(f"✅ Completed: {result.get('file_path', 'unknown')}")
            except Exception as e:
                file_path = getattr(e, "file_path", "unknown")
                logger.error(f"❌ Failed: {file_path} - {e}")
                results[str(file_path)] = {'error': str(e)}
    except KeyboardInterrupt:
        logger.warning("🛑 Interrupted by user. Cancelling remaining tasks…")
        for task in tasks:
            task.cancel()
        raise

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if len(results) == 1:
        file_path = list(results.keys())[0]
        symbol = extract_symbol_from_filename(file_path)
    else:
        symbol = "MULTI"
    output_file = output_dir / f"{symbol}_comprehensive_enhanced.json"

    # Save JSON results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Compress if requested
    if config.compress_output:
        with open(output_file, 'rb') as f_in:
            with gzip.open(f"{output_file}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        output_file.unlink()  # Remove uncompressed file
        logger.info(f"📦 Results compressed and saved to: {output_file}.gz")
    else:
        logger.info(f"💾 Results saved to: {output_file}")

    # Generate summary report
    summary_file = output_dir / f"summary_report_enhanced_{timestamp}.json"
    summary = {
        'total_files_processed': len(files_to_process),
        'successful_analyses': len([r for r in results.values() if 'error' not in r]),
        'failed_analyses': len([r for r in results.values() if 'error' in r]),
        'analysis_timestamp': datetime.now().isoformat(),
        'enhancements': {
            'london_kill_zone_detection': True,
            'fvg_signals_after_displacement': True,
            'comprehensive_metadata_generation': True,
            'zanflow_v12_integration': True
        },
        'configuration': {
            'tick_bars_limit': config.tick_bars_limit,
            'all_features_enabled': True,
            'csv_and_json_processing': True
        },
        'files_processed': list(results.keys())
    }

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info(f"📋 Enhanced summary report saved to: {summary_file}")
    logger.info(f"🎉 ENHANCED ULTIMATE ANALYSIS COMPLETE! Processed {len(files_to_process)} files")
    logger.info(f"✅ Success: {summary['successful_analyses']} | ❌ Failed: {summary['failed_analyses']}")
    logger.info(f"🔥 Enhanced with: London Kill Zone, FVG Signals, ZANFLOW v12 Integration, Comprehensive Metadata")

if __name__ == "__main__":
    asyncio.run(main())