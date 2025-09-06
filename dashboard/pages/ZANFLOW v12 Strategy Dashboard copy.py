#!/usr/bin/env python3
"""
ZANFLOW v12 Strategy-Based Dashboard
SMC Liquidity Sweep • Wyckoff Accumulation • Session Judas Swing
Ultra-Professional Strategy Implementation Dashboard
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
import os
import glob
import re
from collections import defaultdict

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load default parquet directory from Streamlit secrets (./.streamlit/secrets.toml)
# ---------------------------------------------------------------------------
try:
    DEFAULT_DATA_FOLDER = st.secrets.get(
        "parquet_dir",
        "/Users/tom/Documents/_trade/_exports/_tick/parquet/"
    )
except Exception:
    DEFAULT_DATA_FOLDER = "/Users/tom/Documents/_trade/_exports/_tick/parquet/"

PARQUET_DATA_DIR = DEFAULT_DATA_FOLDER  # for external modules / clarity

# ============================================================================
# ZANFLOW v12 STRATEGY CONFIGURATION
# ============================================================================

class ZANFLOWConfig:
    """ZANFLOW v12 Strategy Configuration"""

    STRATEGIES = {
        "SMC_LiquiditySweep_StructureShift_POI_v12": {
            "name": "SMC Liquidity Sweep → Structure Shift → POI Entry",
            "aliases": ["Inducement Sweep POI Reversal", "AlphaRipper Style", "Engineered Liquidity"],
            "tier": "A",
            "description": "HTF Bias → Liquidity Sweep → Sharp Rejection → CHoCH/BoS → FVG/OB Entry",
            "timeframes": {"htf": ["1d", "4h", "1h"], "setup": ["15min", "5min"], "entry": ["1min"]},
            "min_rr": 2.0,
            "confluence_required": 5,
            "color": "#FFD700"
        },
        "Wyckoff_Accumulation_Spring_FVG_Entry_v12": {
            "name": "Wyckoff Accumulation → Spring → FVG Entry",
            "aliases": ["Wyckoff Spring Entry", "Phase C Trap Entry"],
            "tier": "A",
            "description": "Accumulation Context → Spring/Shakeout → Secondary Test → CHoCH → FVG Entry",
            "timeframes": {"htf": ["4h", "1h"], "setup": ["15min", "5min"], "entry": ["1min"]},
            "min_rr": 2.0,
            "confluence_required": 4,
            "color": "#00FF88"
        },
        "Session_JudasSweep_Reversal_v12": {
            "name": "Session Judas Sweep → Reversal",
            "aliases": ["London Judas Swing", "Asia Range Sweep Play"],
            "tier": "A",
            "description": "Asian Range → London Judas Sweep → CHoCH → NY Entry at POI",
            "timeframes": {"context": ["15min", "1h"], "catalyst": ["5min", "15min"], "entry": ["1min", "5min"]},
            "min_rr": 2.0,
            "confluence_required": 4,
            "color": "#FF6B6B"
        }
    }

    SESSIONS = {
        "Asian": {"start": time(22, 0), "end": time(7, 0), "color": "#17a2b8"},
        "London": {"start": time(7, 0), "end": time(16, 0), "color": "#ff6b6b"},
        "New_York": {"start": time(13, 0), "end": time(22, 0), "color": "#28a745"},
        "London_Killzone": {"start": time(7, 0), "end": time(9, 0), "color": "#dc3545"}
    }

def setup_zanflow_page():
    """Setup ZANFLOW v12 professional page styling"""
    st.set_page_config(
        page_title="🏛️ ZANFLOW v12 Strategy Dashboard",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # ZANFLOW v12 Professional Styling
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        .main {
            background: linear-gradient(135deg, #0a0f1c 0%, #1a1f2e 25%, #2d1810 50%, #1a1f2e 75%, #0a0f1c 100%);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }
        
        .zanflow-header {
            background: linear-gradient(135deg, #1a1f2e 0%, #ffd700 15%, #ff8c00 35%, #ffd700 65%, #ff8c00 85%, #1a1f2e 100%);
            padding: 3rem;
            border-radius: 25px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 20px 60px rgba(255, 215, 0, 0.4);
            border: 3px solid rgba(255, 215, 0, 0.5);
            position: relative;
            overflow: hidden;
        }
        
        .zanflow-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: repeating-linear-gradient(
                45deg,
                transparent,
                transparent 15px,
                rgba(255, 255, 255, 0.1) 15px,
                rgba(255, 255, 255, 0.1) 30px
            );
            animation: zanflow-shimmer 4s linear infinite;
            z-index: 1;
        }
        
        .zanflow-header h1, .zanflow-header h2, .zanflow-header p {
            position: relative;
            z-index: 2;
            color: #000;
            font-weight: 800;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        @keyframes zanflow-shimmer {
            0% { transform: translate(-50%, -50%) rotate(0deg); }
            100% { transform: translate(-50%, -50%) rotate(360deg); }
        }
        
        .strategy-tier-a {
            background: linear-gradient(145deg, #1a1f2e, #2a2f3e);
            border: 3px solid #ffd700;
            border-radius: 20px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 15px 40px rgba(255, 215, 0, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .strategy-tier-a::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 215, 0, 0.2), transparent);
            transition: left 0.8s;
        }
        
        .strategy-tier-a:hover::before {
            left: 100%;
        }
        
        .smc-signal {
            background: linear-gradient(45deg, #ffd700, #ffed4e, #ffc107);
            color: #000;
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.6);
            animation: smc-pulse 2.5s infinite;
            border: 3px solid #ff8c00;
        }
        
        @keyframes smc-pulse {
            0%, 100% { 
                box-shadow: 0 10px 30px rgba(255, 215, 0, 0.6);
                transform: scale(1);
            }
            50% { 
                box-shadow: 0 15px 45px rgba(255, 215, 0, 0.9);
                transform: scale(1.02);
            }
        }
        
        .wyckoff-signal {
            background: linear-gradient(45deg, #00ff88, #20c997, #28a745);
            color: #000;
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.6);
            animation: wyckoff-pulse 2.5s infinite;
            border: 3px solid #17a2b8;
        }
        
        @keyframes wyckoff-pulse {
            0%, 100% { 
                box-shadow: 0 10px 30px rgba(0, 255, 136, 0.6);
            }
            50% { 
                box-shadow: 0 15px 45px rgba(0, 255, 136, 0.9);
            }
        }
        
        .session-signal {
            background: linear-gradient(45deg, #ff6b6b, #ee5a52, #dc3545);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            font-weight: 700;
            text-align: center;
            box-shadow: 0 10px 30px rgba(255, 107, 107, 0.6);
            animation: session-pulse 2.5s infinite;
            border: 3px solid #dc3545;
        }
        
        @keyframes session-pulse {
            0%, 100% { 
                box-shadow: 0 10px 30px rgba(255, 107, 107, 0.6);
            }
            50% { 
                box-shadow: 0 15px 45px rgba(255, 107, 107, 0.9);
            }
        }
        
        .confluence-meter {
            background: linear-gradient(145deg, #2a2f3e, #3a3f4e);
            border: 2px solid rgba(255, 215, 0, 0.3);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            text-align: center;
        }
        
        .confluence-bar {
            width: 100%;
            height: 25px;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
            border-radius: 12px;
            position: relative;
            margin: 1rem 0;
        }
        
        .confluence-indicator {
            height: 100%;
            border-radius: 12px;
            background: white;
            position: absolute;
            width: 6px;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
            transition: left 0.3s ease;
        }
        
        .zbar-log {
            background: linear-gradient(145deg, #0a0f1c, #1a1f2e);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .strategy-status {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            margin: 0.3rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .status-active { 
            background: linear-gradient(45deg, #28a745, #20c997); 
            color: white; 
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4);
        }
        .status-monitoring { 
            background: linear-gradient(45deg, #ffc107, #fd7e14); 
            color: #000; 
            box-shadow: 0 4px 15px rgba(255, 193, 7, 0.4);
        }
        .status-inactive { 
            background: linear-gradient(45deg, #6c757d, #495057); 
            color: white; 
            box-shadow: 0 4px 15px rgba(108, 117, 125, 0.4);
        }
        
        .metric-zanflow {
            background: linear-gradient(145deg, #2a2f3e, #3a3f4e);
            padding: 2rem;
            border-radius: 20px;
            border: 2px solid rgba(255, 215, 0, 0.3);
            margin: 1rem 0;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .price-display-zanflow {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(45deg, #ffd700, #ff8c00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
            margin-bottom: 0.5rem;
        }
        
        .chart-container-zanflow {
            background: rgba(0, 0, 0, 0.4);
            border: 2px solid rgba(255, 215, 0, 0.3);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# ZANFLOW v12 STRATEGY ENGINES
# ============================================================================

class SMCLiquiditySweepEngine:
    """SMC Liquidity Sweep → Structure Shift → POI Entry Strategy Engine"""

    def __init__(self):
        self.signals = []
        self.confluence_factors = []

    def analyze_smc_setup(self, df: pd.DataFrame, htf_bias: str = "bullish") -> Dict:
        """Analyze SMC Liquidity Sweep setup"""
        results = {
            "strategy_active": False,
            "confluence_score": 0,
            "signals": [],
            "entry_conditions": {},
            "risk_metrics": {},
            "zbar_logs": []
        }

        if len(df) < 50:
            return results

        # HTF Context Analysis
        htf_context = self._analyze_htf_context(df, htf_bias)

        # Liquidity Sweep Detection
        liquidity_sweeps = self._detect_liquidity_sweeps(df)

        # Structure Shift Analysis (CHoCH/BoS)
        structure_shifts = self._analyze_structure_shifts(df)

        # POI Identification (FVG/Order Blocks)
        poi_zones = self._identify_poi_zones(df)

        # Calculate confluence
        confluence_score = self._calculate_confluence(
            htf_context, liquidity_sweeps, structure_shifts, poi_zones
        )

        results.update({
            "strategy_active": confluence_score >= 5,
            "confluence_score": confluence_score,
            "htf_context": htf_context,
            "liquidity_sweeps": liquidity_sweeps,
            "structure_shifts": structure_shifts,
            "poi_zones": poi_zones,
            "signals": self._generate_smc_signals(df, confluence_score)
        })

        return results

    def _analyze_htf_context(self, df: pd.DataFrame, bias: str) -> Dict:
        """Analyze Higher Timeframe context"""
        context = {
            "bias": bias,
            "trend_strength": 0,
            "key_levels": [],
            "premium_discount": "neutral"
        }

        # Simple trend analysis
        if len(df) >= 50:
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            current_price = df['close'].iloc[-1]

            # Premium/Discount analysis
            range_position = (current_price - recent_low) / (recent_high - recent_low)

            if range_position > 0.7:
                context["premium_discount"] = "premium"
            elif range_position < 0.3:
                context["premium_discount"] = "discount"

            # Trend strength
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else sma_20

            if current_price > sma_20 > sma_50:
                context["trend_strength"] = 0.8
            elif current_price < sma_20 < sma_50:
                context["trend_strength"] = -0.8
            else:
                context["trend_strength"] = 0.3

        return context

    def _detect_liquidity_sweeps(self, df: pd.DataFrame) -> List[Dict]:
        """Detect liquidity sweeps with volume confirmation"""
        sweeps = []

        for i in range(20, len(df)):
            # Look for sweeps of recent highs/lows
            lookback = df.iloc[i-20:i]
            recent_high = lookback['high'].max()
            recent_low = lookback['low'].min()

            current_bar = df.iloc[i]

            # Bullish sweep (sweep low, expect bullish reversal)
            if (current_bar['low'] < recent_low and
                current_bar['close'] > recent_low and
                'volume' in df.columns and
                current_bar['volume'] > df['volume'].iloc[i-10:i].mean() * 1.5):

                sweeps.append({
                    'index': i,
                    'type': 'bullish_sweep',
                    'level': recent_low,
                    'rejection_strength': (current_bar['close'] - current_bar['low']) / (current_bar['high'] - current_bar['low']),
                    'volume_confirmation': True
                })

            # Bearish sweep (sweep high, expect bearish reversal)
            elif (current_bar['high'] > recent_high and
                  current_bar['close'] < recent_high and
                  'volume' in df.columns and
                  current_bar['volume'] > df['volume'].iloc[i-10:i].mean() * 1.5):

                sweeps.append({
                    'index': i,
                    'type': 'bearish_sweep',
                    'level': recent_high,
                    'rejection_strength': (current_bar['high'] - current_bar['close']) / (current_bar['high'] - current_bar['low']),
                    'volume_confirmation': True
                })

        return sweeps[-10:]  # Return last 10 sweeps

    def _analyze_structure_shifts(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze market structure shifts (CHoCH/BoS)"""
        shifts = []

        # Simplified structure shift detection
        for i in range(30, len(df)):
            window = df.iloc[i-20:i+1]

            # Look for significant breaks of structure
            if len(window) >= 20:
                swing_high = window['high'].max()
                swing_low = window['low'].min()
                current_close = df['close'].iloc[i]

                # Bullish CHoCH (Change of Character)
                if (current_close > swing_high and
                    df['close'].iloc[i-1] <= swing_high):

                    shifts.append({
                        'index': i,
                        'type': 'bullish_choch',
                        'level': swing_high,
                        'displacement': current_close - swing_high,
                        'strength': 'high' if abs(current_close - swing_high) > df['close'].std() else 'medium'
                    })

                # Bearish CHoCH
                elif (current_close < swing_low and
                      df['close'].iloc[i-1] >= swing_low):

                    shifts.append({
                        'index': i,
                        'type': 'bearish_choch',
                        'level': swing_low,
                        'displacement': swing_low - current_close,
                        'strength': 'high' if abs(swing_low - current_close) > df['close'].std() else 'medium'
                    })

        return shifts[-5:]  # Return last 5 shifts

    def _identify_poi_zones(self, df: pd.DataFrame) -> List[Dict]:
        """Identify Points of Interest (FVG, Order Blocks)"""
        poi_zones = []

        # Fair Value Gap detection
        for i in range(2, len(df)):
            # Bullish FVG
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                if gap_size > 0.001 * df['close'].iloc[i]:  # Minimum gap threshold
                    poi_zones.append({
                        'index': i,
                        'type': 'bullish_fvg',
                        'top': df['low'].iloc[i],
                        'bottom': df['high'].iloc[i-2],
                        'size': gap_size,
                        'freshness': 'fresh'
                    })

            # Bearish FVG
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                if gap_size > 0.001 * df['close'].iloc[i]:
                    poi_zones.append({
                        'index': i,
                        'type': 'bearish_fvg',
                        'top': df['low'].iloc[i-2],
                        'bottom': df['high'].iloc[i],
                        'size': gap_size,
                        'freshness': 'fresh'
                    })

        # Order Block detection (simplified)
        for i in range(10, len(df) - 1):
            # Bullish Order Block
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # Down candle
                df['close'].iloc[i+1] > df['open'].iloc[i+1] and  # Next candle up
                df['close'].iloc[i+1] > df['high'].iloc[i]):  # Strong move up

                poi_zones.append({
                    'index': i,
                    'type': 'bullish_ob',
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i],
                    'freshness': 'fresh'
                })

            # Bearish Order Block
            elif (df['close'].iloc[i] > df['open'].iloc[i] and  # Up candle
                  df['close'].iloc[i+1] < df['open'].iloc[i+1] and  # Next candle down
                  df['close'].iloc[i+1] < df['low'].iloc[i]):  # Strong move down

                poi_zones.append({
                    'index': i,
                    'type': 'bearish_ob',
                    'top': df['high'].iloc[i],
                    'bottom': df['low'].iloc[i],
                    'freshness': 'fresh'
                })

        return poi_zones[-15:]  # Return last 15 POI zones

    def _calculate_confluence(self, htf_context: Dict, sweeps: List, shifts: List, poi_zones: List) -> int:
        """Calculate confluence score for SMC setup"""
        score = 0

        # HTF bias alignment
        if htf_context.get('trend_strength', 0) > 0.5:
            score += 2

        # Recent liquidity sweep with good rejection
        recent_sweeps = [s for s in sweeps if s.get('rejection_strength', 0) > 0.7]
        if recent_sweeps:
            score += 2

        # Recent structure shift
        if shifts:
            score += 2

        # Fresh POI zones available
        fresh_poi = [p for p in poi_zones if p.get('freshness') == 'fresh']
        if fresh_poi:
            score += 1

        # Premium/Discount alignment
        if htf_context.get('premium_discount') in ['premium', 'discount']:
            score += 1

        return score

    def _generate_smc_signals(self, df: pd.DataFrame, confluence_score: int) -> List[Dict]:
        """Generate SMC trading signals"""
        signals = []

        if confluence_score >= 5:
            latest_price = df['close'].iloc[-1]

            signals.append({
                'timestamp': df.index[-1],
                'strategy': 'SMC_LiquiditySweep_StructureShift_POI_v12',
                'signal_type': 'ENTRY_READY',
                'confluence_score': confluence_score,
                'entry_price': latest_price,
                'confidence': 'HIGH' if confluence_score >= 7 else 'MEDIUM',
                'session': self._get_current_session(),
                'description': f'SMC Setup Ready - Confluence: {confluence_score}/10'
            })

        return signals

    def _get_current_session(self) -> str:
        """Get current trading session"""
        utc_now = datetime.now(pytz.UTC)
        current_time = utc_now.time()

        for session, times in ZANFLOWConfig.SESSIONS.items():
            if times["start"] <= current_time <= times["end"]:
                return session

        return "Off_Hours"

class WyckoffAccumulationEngine:
    """Wyckoff Accumulation → Spring → FVG Entry Strategy Engine"""

    def __init__(self):
        self.signals = []
        self.wyckoff_phases = []

    def analyze_wyckoff_setup(self, df: pd.DataFrame) -> Dict:
        """Analyze Wyckoff Accumulation setup"""
        results = {
            "strategy_active": False,
            "confluence_score": 0,
            "current_phase": "Unknown",
            "signals": [],
            "wyckoff_events": []
        }

        if len(df) < 100:
            return results

        # Detect Wyckoff phases
        phases = self._detect_wyckoff_phases(df)

        # Detect Wyckoff events (Spring, ST, etc.)
        events = self._detect_wyckoff_events(df)

        # Calculate confluence for Wyckoff setup
        confluence_score = self._calculate_wyckoff_confluence(phases, events)

        results.update({
            "strategy_active": confluence_score >= 4,
            "confluence_score": confluence_score,
            "current_phase": phases[-1]['phase'] if phases else "Unknown",
            "wyckoff_phases": phases,
            "wyckoff_events": events,
            "signals": self._generate_wyckoff_signals(df, confluence_score, phases, events)
        })

        return results

    def _detect_wyckoff_phases(self, df: pd.DataFrame) -> List[Dict]:
        """Detect Wyckoff market phases"""
        phases = []

        # Calculate necessary indicators
        df['volume_ma'] = df['volume'].rolling(20).mean() if 'volume' in df.columns else 1
        df['price_volatility'] = df['close'].rolling(20).std()
        df['price_range'] = df['high'] - df['low']

        for i in range(50, len(df)):
            window = df.iloc[i-20:i+1]

            avg_volume = window['volume_ma'].mean() if 'volume' in df.columns else 1
            price_range = window['high'].max() - window['low'].min()
            trend_strength = abs(window['close'].iloc[-1] - window['close'].iloc[0]) / price_range if price_range > 0 else 0

            # Accumulation: High volume, low volatility, sideways price
            if ('volume' in df.columns and
                window['volume'].mean() > avg_volume * 1.2 and
                window['price_volatility'].mean() < df['price_volatility'].quantile(0.3) and
                trend_strength < 0.3):

                phases.append({
                    'index': i,
                    'phase': 'Accumulation',
                    'strength': window['volume'].mean() / avg_volume if avg_volume > 0 else 1,
                    'price_level': window['close'].mean(),
                    'description': 'Smart money accumulation phase'
                })

            # Markup: Rising prices with good volume
            elif ('volume' in df.columns and
                  window['close'].iloc[-1] > window['close'].iloc[0] * 1.02 and
                  window['volume'].mean() > avg_volume):

                phases.append({
                    'index': i,
                    'phase': 'Markup',
                    'strength': trend_strength,
                    'price_level': window['close'].mean(),
                    'description': 'Markup phase - trend continuation'
                })

        return phases[-10:]  # Return last 10 phases

    def _detect_wyckoff_events(self, df: pd.DataFrame) -> List[Dict]:
        """Detect specific Wyckoff events"""
        events = []

        for i in range(20, len(df)):
            if 'volume' not in df.columns:
                continue

            volume_ma = df['volume'].rolling(20).mean().iloc[i]

            # Spring: Test below support with lower volume and rejection
            if (df['low'].iloc[i] < df['low'].iloc[i-10:i].min() and
                df['volume'].iloc[i] < volume_ma and
                df['close'].iloc[i] > df['low'].iloc[i]):

                events.append({
                    'index': i,
                    'event': 'Spring',
                    'price': df['low'].iloc[i],
                    'volume_ratio': df['volume'].iloc[i] / volume_ma,
                    'description': 'Spring - Test of support with rejection',
                    'significance': 'High'
                })

            # Secondary Test: Retest of Spring on low volume
            elif (i > 5 and
                  abs(df['low'].iloc[i] - df['low'].iloc[i-5:i].min()) < df['close'].std() * 0.5 and
                  df['volume'].iloc[i] < volume_ma * 0.8):

                events.append({
                    'index': i,
                    'event': 'Secondary_Test',
                    'price': df['low'].iloc[i],
                    'volume_ratio': df['volume'].iloc[i] / volume_ma,
                    'description': 'Secondary Test - Low volume retest',
                    'significance': 'Medium'
                })

        return events[-10:]  # Return last 10 events

    def _calculate_wyckoff_confluence(self, phases: List, events: List) -> int:
        """Calculate confluence score for Wyckoff setup"""
        score = 0

        # Recent accumulation phase
        recent_accumulation = [p for p in phases if p['phase'] == 'Accumulation']
        if recent_accumulation:
            score += 2

        # Spring event detected
        spring_events = [e for e in events if e['event'] == 'Spring']
        if spring_events:
            score += 2

        # Secondary test after spring
        st_events = [e for e in events if e['event'] == 'Secondary_Test']
        if st_events and spring_events:
            score += 1

        # Volume characteristics
        if events:
            low_volume_events = [e for e in events if e.get('volume_ratio', 1) < 0.8]
            if low_volume_events:
                score += 1

        return score

    def _generate_wyckoff_signals(self, df: pd.DataFrame, confluence_score: int, phases: List, events: List) -> List[Dict]:
        """Generate Wyckoff trading signals"""
        signals = []

        if confluence_score >= 4:
            latest_price = df['close'].iloc[-1]
            current_phase = phases[-1]['phase'] if phases else "Unknown"

            signals.append({
                'timestamp': df.index[-1],
                'strategy': 'Wyckoff_Accumulation_Spring_FVG_Entry_v12',
                'signal_type': 'WYCKOFF_SETUP',
                'confluence_score': confluence_score,
                'current_phase': current_phase,
                'entry_price': latest_price,
                'confidence': 'HIGH' if confluence_score >= 6 else 'MEDIUM',
                'description': f'Wyckoff {current_phase} - Confluence: {confluence_score}/8'
            })

        return signals

class SessionJudasSweepEngine:
    """Session Judas Sweep → Reversal Strategy Engine"""

    def __init__(self):
        self.signals = []
        self.session_ranges = {}

    def analyze_session_setup(self, df: pd.DataFrame) -> Dict:
        """Analyze Session Judas Sweep setup"""
        results = {
            "strategy_active": False,
            "confluence_score": 0,
            "current_session": "Unknown",
            "signals": [],
            "session_analysis": {}
        }

        if len(df) < 50:
            return results

        # Identify session ranges
        session_ranges = self._identify_session_ranges(df)

        # Detect Judas sweeps
        judas_sweeps = self._detect_judas_sweeps(df, session_ranges)

        # Analyze session reversals
        session_reversals = self._analyze_session_reversals(df, judas_sweeps)

        # Calculate confluence
        confluence_score = self._calculate_session_confluence(session_ranges, judas_sweeps, session_reversals)

        results.update({
            "strategy_active": confluence_score >= 4,
            "confluence_score": confluence_score,
            "current_session": self._get_current_session(),
            "session_ranges": session_ranges,
            "judas_sweeps": judas_sweeps,
            "session_reversals": session_reversals,
            "signals": self._generate_session_signals(df, confluence_score)
        })

        return results

    def _identify_session_ranges(self, df: pd.DataFrame) -> Dict:
        """Identify Asian session ranges and key levels"""
        ranges = {}

        # Simplified session range identification
        if len(df) >= 24:  # Assuming hourly data
            asian_data = df.tail(24)  # Last 24 hours as proxy

            ranges['asian_high'] = asian_data['high'].max()
            ranges['asian_low'] = asian_data['low'].min()
            ranges['asian_range'] = ranges['asian_high'] - ranges['asian_low']
            ranges['current_price'] = df['close'].iloc[-1]

            # Determine position in range
            if ranges['asian_range'] > 0:
                ranges['range_position'] = (ranges['current_price'] - ranges['asian_low']) / ranges['asian_range']
            else:
                ranges['range_position'] = 0.5

        return ranges

    def _detect_judas_sweeps(self, df: pd.DataFrame, session_ranges: Dict) -> List[Dict]:
        """Detect Judas sweeps of session ranges"""
        sweeps = []

        if not session_ranges:
            return sweeps

        asian_high = session_ranges.get('asian_high', 0)
        asian_low = session_ranges.get('asian_low', 0)

        for i in range(10, len(df)):
            current_bar = df.iloc[i]

            # Judas sweep above Asian high
            if (current_bar['high'] > asian_high and
                current_bar['close'] < asian_high and
                'volume' in df.columns and
                current_bar['volume'] > df['volume'].iloc[i-5:i].mean() * 1.3):

                sweeps.append({
                    'index': i,
                    'type': 'judas_sweep_high',
                    'level': asian_high,
                    'sweep_high': current_bar['high'],
                    'rejection_strength': (asian_high - current_bar['close']) / (current_bar['high'] - current_bar['low']),
                    'volume_confirmation': True
                })

            # Judas sweep below Asian low
            elif (current_bar['low'] < asian_low and
                  current_bar['close'] > asian_low and
                  'volume' in df.columns and
                  current_bar['volume'] > df['volume'].iloc[i-5:i].mean() * 1.3):

                sweeps.append({
                    'index': i,
                    'type': 'judas_sweep_low',
                    'level': asian_low,
                    'sweep_low': current_bar['low'],
                    'rejection_strength': (current_bar['close'] - asian_low) / (current_bar['high'] - current_bar['low']),
                    'volume_confirmation': True
                })

        return sweeps[-5:]  # Return last 5 sweeps

    def _analyze_session_reversals(self, df: pd.DataFrame, judas_sweeps: List) -> List[Dict]:
        """Analyze reversals after Judas sweeps"""
        reversals = []

        for sweep in judas_sweeps:
            sweep_index = sweep['index']

            # Look for reversal in next few bars
            for j in range(sweep_index + 1, min(sweep_index + 10, len(df))):
                current_close = df['close'].iloc[j]

                if sweep['type'] == 'judas_sweep_high':
                    # Look for bearish reversal
                    if current_close < sweep['level'] * 0.995:  # 0.5% below swept level
                        reversals.append({
                            'index': j,
                            'type': 'bearish_reversal',
                            'sweep_reference': sweep_index,
                            'reversal_strength': (sweep['level'] - current_close) / sweep['level'],
                            'description': 'Bearish reversal after high sweep'
                        })
                        break

                elif sweep['type'] == 'judas_sweep_low':
                    # Look for bullish reversal
                    if current_close > sweep['level'] * 1.005:  # 0.5% above swept level
                        reversals.append({
                            'index': j,
                            'type': 'bullish_reversal',
                            'sweep_reference': sweep_index,
                            'reversal_strength': (current_close - sweep['level']) / sweep['level'],
                            'description': 'Bullish reversal after low sweep'
                        })
                        break

        return reversals

    def _calculate_session_confluence(self, session_ranges: Dict, judas_sweeps: List, reversals: List) -> int:
        """Calculate confluence score for session setup"""
        score = 0

        # Clear Asian range identified
        if session_ranges.get('asian_range', 0) > 0:
            score += 1

        # Recent Judas sweep with good rejection
        recent_sweeps = [s for s in judas_sweeps if s.get('rejection_strength', 0) > 0.6]
        if recent_sweeps:
            score += 2

        # Reversal confirmed after sweep
        if reversals:
            score += 2

        # Volume confirmation on sweeps
        volume_confirmed_sweeps = [s for s in judas_sweeps if s.get('volume_confirmation', False)]
        if volume_confirmed_sweeps:
            score += 1

        return score

    def _generate_session_signals(self, df: pd.DataFrame, confluence_score: int) -> List[Dict]:
        """Generate session trading signals"""
        signals = []

        if confluence_score >= 4:
            latest_price = df['close'].iloc[-1]
            current_session = self._get_current_session()

            signals.append({
                'timestamp': df.index[-1],
                'strategy': 'Session_JudasSweep_Reversal_v12',
                'signal_type': 'SESSION_REVERSAL',
                'confluence_score': confluence_score,
                'current_session': current_session,
                'entry_price': latest_price,
                'confidence': 'HIGH' if confluence_score >= 6 else 'MEDIUM',
                'description': f'Session Reversal Setup - {current_session} - Confluence: {confluence_score}/6'
            })

        return signals

    def _get_current_session(self) -> str:
        """Get current trading session"""
        utc_now = datetime.now(pytz.UTC)
        current_time = utc_now.time()

        for session, times in ZANFLOWConfig.SESSIONS.items():
            if times["start"] <= current_time <= times["end"]:
                return session

        return "Off_Hours"

# ============================================================================
# ZANFLOW v12 ORCHESTRATOR
# ============================================================================

class ZANFLOWOrchestrator:
    """ZANFLOW v12 Strategy Orchestrator"""

    def __init__(self):
        self.smc_engine = SMCLiquiditySweepEngine()
        self.wyckoff_engine = WyckoffAccumulationEngine()
        self.session_engine = SessionJudasSweepEngine()
        self.zbar_logs = []

    def run_comprehensive_analysis(self, df: pd.DataFrame, selected_strategies: List[str]) -> Dict:
        """Run comprehensive ZANFLOW v12 analysis"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'strategies': {},
            'overall_signals': [],
            'zbar_logs': [],
            'market_context': self._analyze_market_context(df)
        }

        # Run selected strategies
        if "SMC_LiquiditySweep_StructureShift_POI_v12" in selected_strategies:
            results['strategies']['smc'] = self.smc_engine.analyze_smc_setup(df)

        if "Wyckoff_Accumulation_Spring_FVG_Entry_v12" in selected_strategies:
            results['strategies']['wyckoff'] = self.wyckoff_engine.analyze_wyckoff_setup(df)

        if "Session_JudasSweep_Reversal_v12" in selected_strategies:
            results['strategies']['session'] = self.session_engine.analyze_session_setup(df)

        # Compile overall signals
        for strategy_name, strategy_results in results['strategies'].items():
            if strategy_results.get('signals'):
                results['overall_signals'].extend(strategy_results['signals'])

        # Generate ZBAR logs
        results['zbar_logs'] = self._generate_zbar_logs(results)

        return results

    def _analyze_market_context(self, df: pd.DataFrame) -> Dict:
        """Analyze overall market context"""
        context = {
            'current_price': df['close'].iloc[-1],
            'volatility': df['close'].rolling(20).std().iloc[-1],
            'trend': 'neutral',
            'session': self._get_current_session(),
            'volume_profile': 'normal'
        }

        # Simple trend analysis
        if len(df) >= 50:
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-1]

            if context['current_price'] > sma_20 > sma_50:
                context['trend'] = 'bullish'
            elif context['current_price'] < sma_20 < sma_50:
                context['trend'] = 'bearish'

        # Volume analysis
        if 'volume' in df.columns:
            recent_volume = df['volume'].tail(10).mean()
            avg_volume = df['volume'].mean()

            if recent_volume > avg_volume * 1.5:
                context['volume_profile'] = 'high'
            elif recent_volume < avg_volume * 0.7:
                context['volume_profile'] = 'low'

        return context

    def _generate_zbar_logs(self, results: Dict) -> List[Dict]:
        """Generate ZBAR (Zanalytics Behavioral Analysis and Reflection) logs"""
        logs = []

        for strategy_name, strategy_results in results['strategies'].items():
            if strategy_results.get('strategy_active'):
                logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'strategy': strategy_name,
                    'status': 'ACTIVE',
                    'confluence_score': strategy_results.get('confluence_score', 0),
                    'signals_count': len(strategy_results.get('signals', [])),
                    'market_context': results['market_context'],
                    'session': results['market_context']['session']
                })

        return logs

    def _get_current_session(self) -> str:
        """Get current trading session"""
        utc_now = datetime.now(pytz.UTC)
        current_time = utc_now.time()

        for session, times in ZANFLOWConfig.SESSIONS.items():
            if times["start"] <= current_time <= times["end"]:
                return session

        return "Off_Hours"

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_zanflow_master_chart(df: pd.DataFrame, analysis_results: Dict, symbol: str, timeframe: str) -> go.Figure:
    """Create ZANFLOW v12 master analysis chart"""

    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=(
            f'{symbol} {timeframe} - ZANFLOW v12 Strategy Analysis',
            'Volume & Session Analysis',
            'SMC Structure & Signals',
            'Wyckoff Phase Analysis',
            'Strategy Confluence Matrix'
        ),
        row_heights=[0.4, 0.2, 0.15, 0.15, 0.1]
    )

    # Main price chart
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
            decreasing_fillcolor='rgba(139, 0, 0, 0.8)'
        ),
        row=1, col=1
    )

    # Add moving averages
    if len(df) >= 20:
        sma_20 = df['close'].rolling(20).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma_20,
                mode='lines', name='SMA 20',
                line=dict(color='#FFD700', width=2)
            ),
            row=1, col=1
        )

    if len(df) >= 50:
        sma_50 = df['close'].rolling(50).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index, y=sma_50,
                mode='lines', name='SMA 50',
                line=dict(color='#FF8C00', width=2)
            ),
            row=1, col=1
        )

    # Add strategy signals
    for strategy_name, strategy_results in analysis_results.get('strategies', {}).items():
        if strategy_results.get('signals'):
            for signal in strategy_results['signals']:
                color = ZANFLOWConfig.STRATEGIES[signal['strategy']]['color']

                fig.add_trace(
                    go.Scatter(
                        x=[signal['timestamp']],
                        y=[signal['entry_price']],
                        mode='markers',
                        marker=dict(
                            symbol='star',
                            size=20,
                            color=color,
                            line=dict(color='white', width=2)
                        ),
                        name=f"{strategy_name.upper()} Signal",
                        hovertemplate=f'<b>{signal["signal_type"]}</b><br>' +
                                    f'Strategy: {signal["strategy"]}<br>' +
                                    f'Confidence: {signal["confidence"]}<br>' +
                                    f'Confluence: {signal.get("confluence_score", 0)}<br>' +
                                    f'Price: ${signal["entry_price"]:.2f}<extra></extra>',
                        showlegend=False
                    ),
                    row=1, col=1
                )

    # Volume analysis
    if 'volume' in df.columns:
        colors = ['#2c5530' if close >= open_price else '#8B0000'
                 for close, open_price in zip(df['close'], df['open'])]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )

    # SMC Analysis
    smc_results = analysis_results.get('strategies', {}).get('smc', {})
    if smc_results:
        # Plot liquidity sweeps
        sweeps = smc_results.get('liquidity_sweeps', [])
        for sweep in sweeps:
            if sweep['index'] < len(df):
                color = '#00FF88' if 'bullish' in sweep['type'] else '#FF6B6B'
                fig.add_trace(
                    go.Scatter(
                        x=[df.index[sweep['index']]],
                        y=[sweep['level']],
                        mode='markers',
                        marker=dict(symbol='triangle-up' if 'bullish' in sweep['type'] else 'triangle-down',
                                  size=12, color=color),
                        name=f"Liquidity Sweep",
                        showlegend=False
                    ),
                    row=3, col=1
                )

    # Wyckoff Analysis
    wyckoff_results = analysis_results.get('strategies', {}).get('wyckoff', {})
    if wyckoff_results:
        phases = wyckoff_results.get('wyckoff_phases', [])
        phase_colors = {'Accumulation': '#28a745', 'Markup': '#17a2b8', 'Distribution': '#ffc107', 'Markdown': '#dc3545'}

        for phase in phases:
            if phase['index'] < len(df):
                color = phase_colors.get(phase['phase'], '#6c757d')
                fig.add_trace(
                    go.Scatter(
                        x=[df.index[phase['index']]],
                        y=[phase['price_level']],
                        mode='markers',
                        marker=dict(symbol='circle', size=10, color=color),
                        name=f"Wyckoff {phase['phase']}",
                        showlegend=False
                    ),
                    row=4, col=1
                )

    # Strategy confluence matrix
    confluence_data = []
    strategy_names = []

    for strategy_name, strategy_results in analysis_results.get('strategies', {}).items():
        confluence_score = strategy_results.get('confluence_score', 0)
        confluence_data.append(confluence_score)
        strategy_names.append(strategy_name.upper())

    if confluence_data:
        fig.add_trace(
            go.Bar(
                x=strategy_names,
                y=confluence_data,
                name='Confluence Scores',
                marker_color=['#28a745' if x >= 5 else '#ffc107' if x >= 3 else '#dc3545' for x in confluence_data],
                opacity=0.8
            ),
            row=5, col=1
        )

    # Update layout
    fig.update_layout(
        title=dict(
            text=f'🏛️ ZANFLOW v12 - {symbol} {timeframe} Strategy Analysis',
            font=dict(size=24, color='#FFD700', family='Inter'),
            x=0.5
        ),
        template='plotly_dark',
        height=1000,
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
        plot_bgcolor='rgba(10, 15, 28, 0.95)'
    )

    # Update axes
    fig.update_yaxes(title_text="Price (USD)", row=1, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="SMC Levels", row=3, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Wyckoff Phases", row=4, col=1, gridcolor='rgba(255,215,0,0.1)')
    fig.update_yaxes(title_text="Confluence", row=5, col=1, gridcolor='rgba(255,215,0,0.1)')

    fig.update_xaxes(gridcolor='rgba(255,215,0,0.1)')

    return fig

def create_strategy_performance_dashboard(analysis_results: Dict) -> go.Figure:
    """Create strategy performance dashboard"""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Strategy Confluence Scores',
            'Signal Distribution',
            'Session Activity',
            'Market Context'
        ),
        specs=[[{"type": "bar"}, {"type": "pie"}],
               [{"type": "bar"}, {"type": "scatter"}]]
    )

    # Strategy confluence scores
    strategies = []
    scores = []
    colors = []

    for strategy_name, strategy_results in analysis_results.get('strategies', {}).items():
        strategies.append(strategy_name.replace('_', ' ').title())
        scores.append(strategy_results.get('confluence_score', 0))

        # Color based on strategy
        if 'smc' in strategy_name:
            colors.append('#FFD700')
        elif 'wyckoff' in strategy_name:
            colors.append('#00FF88')
        elif 'session' in strategy_name:
            colors.append('#FF6B6B')
        else:
            colors.append('#6c757d')

    if strategies:
        fig.add_trace(
            go.Bar(
                x=strategies,
                y=scores,
                marker_color=colors,
                name='Confluence Scores',
                text=[f'{s}/10' for s in scores],
                textposition='auto'
            ),
            row=1, col=1
        )

    # Signal distribution
    signal_types = []
    signal_counts = []

    for strategy_results in analysis_results.get('strategies', {}).values():
        for signal in strategy_results.get('signals', []):
            signal_type = signal.get('signal_type', 'Unknown')
            if signal_type in signal_types:
                idx = signal_types.index(signal_type)
                signal_counts[idx] += 1
            else:
                signal_types.append(signal_type)
                signal_counts.append(1)

    if signal_types:
        fig.add_trace(
            go.Pie(
                labels=signal_types,
                values=signal_counts,
                hole=0.4,
                marker_colors=['#FFD700', '#00FF88', '#FF6B6B', '#17a2b8'],
                name="Signal Distribution"
            ),
            row=1, col=2
        )

    # Session activity
    sessions = list(ZANFLOWConfig.SESSIONS.keys())
    activity = [3, 8, 6, 9]  # Example activity levels
    session_colors = [ZANFLOWConfig.SESSIONS[s]['color'] for s in sessions]

    fig.add_trace(
        go.Bar(
            x=sessions,
            y=activity,
            marker_color=session_colors,
            name='Session Activity',
            opacity=0.8
        ),
        row=2, col=1
    )

    # Market context
    market_context = analysis_results.get('market_context', {})

    context_metrics = ['Volatility', 'Trend Strength', 'Volume Profile']
    context_values = [
        market_context.get('volatility', 0) * 1000,  # Scale for visibility
        0.7 if market_context.get('trend') == 'bullish' else -0.7 if market_context.get('trend') == 'bearish' else 0,
        1.0 if market_context.get('volume_profile') == 'high' else -1.0 if market_context.get('volume_profile') == 'low' else 0
    ]

    fig.add_trace(
        go.Scatter(
            x=context_metrics,
            y=context_values,
            mode='markers+lines',
            marker=dict(size=15, color='#FFD700'),
            line=dict(color='#FFD700', width=3),
            name='Market Context'
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
# MAIN STREAMLIT APPLICATION
# ============================================================================

def main():
    """Main ZANFLOW v12 Strategy Dashboard Application"""

    # Setup page
    setup_zanflow_page()

    # Header
    st.markdown("""
        <div class="zanflow-header">
            <h1>🏛️ ZANFLOW v12</h1>
            <h2>STRATEGY-BASED TRADING DASHBOARD</h2>
            <p>SMC Liquidity Sweep • Wyckoff Accumulation • Session Judas Swing</p>
            <p><strong>INSTITUTIONAL GRADE STRATEGY IMPLEMENTATION</strong></p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar configuration (add data folder selection)
    with st.sidebar:
        # ------------------------------------------------------------------
        # Data folder selection (auto‑defaults from TOML)
        # ------------------------------------------------------------------
        st.markdown("### 📂 Data Location")
        data_folder = st.text_input(
            "Base folder for Parquet/CSV files",
            value=DEFAULT_DATA_FOLDER,
            help="Folder where your time‑series parquet files live"
        )

        # Scan for symbols as subfolders in the data folder
        symbols_found = sorted(
            [d.name.upper() for d in Path(data_folder).iterdir() if d.is_dir()]
        )

        st.markdown("### 💱 Trading Pair")
        selected_symbol = st.selectbox(
            "💱 Select Pair",
            options=symbols_found or ["<No pairs found>"],
            index=0,
            help="Choose a trading pair detected in the data folder"
        )
    # Load data
    with st.spinner("🔄 Loading ZANFLOW v12 data..."):
        try:
            # Dynamically discover parquet files within the symbol subfolder
            symbol_dir = os.path.join(data_folder, selected_symbol)
            parquet_files = glob.glob(os.path.join(symbol_dir, f'{selected_symbol}_*.parquet'))
            timeframes = {}
            tf_pattern = re.compile(fr'{selected_symbol}_(\d+(?:min|h|d))\.parquet', re.IGNORECASE)
            for pf in parquet_files:
                match = tf_pattern.search(Path(pf).name)
                if match:
                    tf = match.group(1).lower()
                    timeframes[tf] = pf

            if not timeframes:
                st.error(f"❌ No {selected_symbol} parquet files found in **{symbol_dir}**. "
                         "Please verify the location or adjust the Data Location above.")
                return

            data = {}
            for tf, filename in timeframes.items():
                try:
                    df = pd.read_parquet(filename)

                    # Ensure proper datetime index
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)

                    # Normalize column names
                    df.columns = df.columns.str.lower()

                    # Basic validation
                    required_cols = ['open', 'high', 'low', 'close']
                    if not all(col in df.columns for col in required_cols):
                        st.warning(f"Missing required columns in {filename}")
                        continue

                    data[tf] = df

                except Exception as e:
                    st.warning(f"Could not load {filename}: {e}")

        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

    # Initialize ZANFLOW orchestrator
    orchestrator = ZANFLOWOrchestrator()

    # Sidebar configuration
    with st.sidebar:
        st.markdown("### 🎛️ ZANFLOW v12 Strategy Controls")

        # Timeframe selection
        selected_timeframe = st.selectbox(
            "📊 Primary Analysis Timeframe",
            options=list(data.keys()),
            index=len(data)-1,
            help="Select primary timeframe for strategy analysis"
        )

        # Strategy selection
        st.markdown("### 🎯 Active Strategies")

        strategy_configs = ZANFLOWConfig.STRATEGIES
        selected_strategies = []

        for strategy_key, strategy_info in strategy_configs.items():
            enabled = st.checkbox(
                f"**{strategy_info['name']}**",
                value=True,
                help=f"Tier {strategy_info['tier']} - {strategy_info['description']}"
            )
            if enabled:
                selected_strategies.append(strategy_key)

                # Show strategy details
                with st.expander(f"📋 {strategy_info['name']} Details"):
                    st.markdown(f"**Aliases**: {', '.join(strategy_info['aliases'])}")
                    st.markdown(f"**Min R:R**: {strategy_info['min_rr']}")
                    st.markdown(f"**Confluence Required**: {strategy_info['confluence_required']}")
                    st.markdown(f"**Timeframes**: {strategy_info['timeframes']}")

        # Analysis options
        st.markdown("### 🔍 Analysis Options")

        confluence_threshold = st.slider(
            "Confluence Threshold",
            min_value=1, max_value=10, value=5,
            help="Minimum confluence score for signal generation"
        )

        show_all_timeframes = st.checkbox("Multi-Timeframe Matrix", value=False)
        show_zbar_logs = st.checkbox("ZBAR Analysis Logs", value=True)
        show_performance = st.checkbox("Strategy Performance", value=True)

        # Current session info
        st.markdown("---")
        st.markdown("### 📊 Session Information")

        current_time = datetime.now(pytz.UTC)
        ny_time = current_time.astimezone(pytz.timezone('America/New_York'))
        london_time = current_time.astimezone(pytz.timezone('Europe/London'))

        st.markdown(f"**UTC**: {current_time.strftime('%H:%M:%S')}")
        st.markdown(f"**NY**: {ny_time.strftime('%H:%M:%S')}")
        st.markdown(f"**London**: {london_time.strftime('%H:%M:%S')}")

        # Current session detection
        current_session = "Off_Hours"
        for session, times in ZANFLOWConfig.SESSIONS.items():
            if times["start"] <= current_time.time() <= times["end"]:
                current_session = session
                break

        session_color = ZANFLOWConfig.SESSIONS.get(current_session, {}).get("color", "#6c757d")
        st.markdown(f"**Current Session**: <span style='color: {session_color}; font-weight: bold;'>{current_session}</span>",
                   unsafe_allow_html=True)

    # Main content area
    current_df = data[selected_timeframe]

    # Display current market metrics
    latest = current_df.iloc[-1]
    current_price = latest['close']

    if len(current_df) > 1:
        price_change = current_price - current_df.iloc[-2]['close']
        price_change_pct = (price_change / current_df.iloc[-2]['close']) * 100
    else:
        price_change = 0
        price_change_pct = 0

    # Key metrics display
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
            <div class="metric-zanflow">
                <div class="price-display-zanflow">${current_price:.2f}</div>
                <div>{selected_symbol} Current</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        change_color = "#28a745" if price_change >= 0 else "#dc3545"
        st.markdown(f"""
            <div class="metric-zanflow">
                <div style="color: {change_color}; font-size: 2rem; font-weight: bold;">
                    {price_change:+.2f}
                </div>
                <div>Change ({price_change_pct:+.2f}%)</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-zanflow">
                <div style="font-size: 2rem; font-weight: bold; color: #FFD700;">
                    ${latest['high']:.2f}
                </div>
                <div>Session High</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="metric-zanflow">
                <div style="font-size: 2rem; font-weight: bold; color: #FF8C00;">
                    ${latest['low']:.2f}
                </div>
                <div>Session Low</div>
            </div>
        """, unsafe_allow_html=True)

    with col5:
        volume = latest.get('volume', 0)
        st.markdown(f"""
            <div class="metric-zanflow">
                <div style="font-size: 2rem; font-weight: bold; color: #17a2b8;">
                    {volume:,.0f}
                </div>
                <div>Volume</div>
            </div>
        """, unsafe_allow_html=True)

    # Strategy execution button
    if st.button("🚀 Execute ZANFLOW v12 Strategy Analysis", type="primary"):
        with st.spinner("🧠 Running comprehensive strategy analysis..."):

            # Run orchestrated analysis
            analysis_results = orchestrator.run_comprehensive_analysis(current_df, selected_strategies)

            # Display strategy status overview
            st.subheader("🎯 Strategy Status Overview")

            strategy_cols = st.columns(len(selected_strategies))

            for i, strategy_key in enumerate(selected_strategies):
                with strategy_cols[i]:
                    strategy_info = ZANFLOWConfig.STRATEGIES[strategy_key]
                    strategy_results = analysis_results['strategies'].get(strategy_key.split('_')[0], {})

                    is_active = strategy_results.get('strategy_active', False)
                    confluence_score = strategy_results.get('confluence_score', 0)

                    status_class = "status-active" if is_active else "status-monitoring" if confluence_score >= 3 else "status-inactive"
                    status_text = "ACTIVE" if is_active else "MONITORING" if confluence_score >= 3 else "INACTIVE"

                    st.markdown(f"""
                        <div class="strategy-tier-a">
                            <h4 style="color: {strategy_info['color']};">{strategy_info['name']}</h4>
                            <div class="strategy-status {status_class}">
                                {status_text}
                            </div>
                            <div class="confluence-meter">
                                <div>Confluence: {confluence_score}/{strategy_info['confluence_required']}</div>
                                <div class="confluence-bar">
                                    <div class="confluence-indicator" style="left: {min(confluence_score * 10, 100)}%;"></div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

            # Display active signals
            if analysis_results['overall_signals']:
                st.subheader("🚨 Active Trading Signals")

                for signal in analysis_results['overall_signals']:
                    strategy_name = signal['strategy']
                    strategy_info = ZANFLOWConfig.STRATEGIES.get(strategy_name, {})
                    signal_color = strategy_info.get('color', '#FFD700')

                    if 'SMC' in strategy_name:
                        signal_class = "smc-signal"
                    elif 'Wyckoff' in strategy_name:
                        signal_class = "wyckoff-signal"
                    elif 'Session' in strategy_name:
                        signal_class = "session-signal"
                    else:
                        signal_class = "smc-signal"

                    st.markdown(f"""
                        <div class="{signal_class}">
                            <h3>🎯 {signal['signal_type']} DETECTED</h3>
                            <p><strong>Strategy:</strong> {strategy_name}</p>
                            <p><strong>Confidence:</strong> {signal['confidence']} | <strong>Confluence:</strong> {signal.get('confluence_score', 'N/A')}</p>
                            <p><strong>Entry Price:</strong> ${signal['entry_price']:.2f}</p>
                            <p><strong>Session:</strong> {signal.get('session', current_session)} | <strong>Time:</strong> {signal['timestamp']}</p>
                            <p><strong>Description:</strong> {signal.get('description', 'High-probability setup identified')}</p>
                        </div>
                    """, unsafe_allow_html=True)

            # Strategy-specific analysis
            for strategy_key in selected_strategies:
                strategy_short = strategy_key.split('_')[0]
                strategy_results = analysis_results['strategies'].get(strategy_short, {})
                strategy_info = ZANFLOWConfig.STRATEGIES[strategy_key]

                if strategy_results:
                    st.subheader(f"📊 {strategy_info['name']} Analysis")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**📈 Strategy Metrics**")
                        st.metric("Confluence Score", f"{strategy_results.get('confluence_score', 0)}/10")
                        st.metric("Strategy Status", "ACTIVE" if strategy_results.get('strategy_active', False) else "MONITORING")

                        if 'current_phase' in strategy_results:
                            st.metric("Current Phase", strategy_results['current_phase'])

                    with col2:
                        st.markdown("**🔍 Analysis Details**")

                        if strategy_short == 'smc':
                            smc_data = strategy_results
                            st.write(f"• Liquidity Sweeps: {len(smc_data.get('liquidity_sweeps', []))}")
                            st.write(f"• Structure Shifts: {len(smc_data.get('structure_shifts', []))}")
                            st.write(f"• POI Zones: {len(smc_data.get('poi_zones', []))}")

                        elif strategy_short == 'wyckoff':
                            wyckoff_data = strategy_results
                            st.write(f"• Wyckoff Phases: {len(wyckoff_data.get('wyckoff_phases', []))}")
                            st.write(f"• Wyckoff Events: {len(wyckoff_data.get('wyckoff_events', []))}")
                            st.write(f"• Current Phase: {wyckoff_data.get('current_phase', 'Unknown')}")

                        elif strategy_short == 'session':
                            session_data = strategy_results
                            st.write(f"• Session Ranges: {len(session_data.get('session_ranges', {}))}")
                            st.write(f"• Judas Sweeps: {len(session_data.get('judas_sweeps', []))}")
                            st.write(f"• Session Reversals: {len(session_data.get('session_reversals', []))}")

            # Master chart
            st.markdown('<div class="chart-container-zanflow">', unsafe_allow_html=True)
            st.subheader("📊 ZANFLOW v12 Master Strategy Chart")

            master_chart = create_zanflow_master_chart(
                current_df,
                analysis_results,
                selected_symbol,
                selected_timeframe
            )

            st.plotly_chart(master_chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Strategy performance dashboard
            if show_performance:
                st.subheader("📈 Strategy Performance Dashboard")

                performance_chart = create_strategy_performance_dashboard(analysis_results)
                st.plotly_chart(performance_chart, use_container_width=True)

            # Multi-timeframe analysis
            if show_all_timeframes:
                st.subheader("🔄 Multi-Timeframe Strategy Matrix")

                mtf_cols = st.columns(len(data))
                for i, (tf, df_tf) in enumerate(data.items()):
                    with mtf_cols[i]:
                        # Quick analysis for each timeframe
                        tf_results = orchestrator.run_comprehensive_analysis(df_tf.tail(100), selected_strategies)

                        active_strategies = sum(1 for s in tf_results['strategies'].values() if s.get('strategy_active', False))
                        total_confluence = sum(s.get('confluence_score', 0) for s in tf_results['strategies'].values())

                        signal_strength = "HIGH" if active_strategies > 0 else "MEDIUM" if total_confluence > 10 else "LOW"
                        signal_color = "#28a745" if signal_strength == "HIGH" else "#ffc107" if signal_strength == "MEDIUM" else "#6c757d"

                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; text-align: center; border: 2px solid {signal_color};">
                                <h4>{tf.upper()}</h4>
                                <div style="color: {signal_color}; font-weight: bold; font-size: 1.2rem;">
                                    {signal_strength}
                                </div>
                                <div>Active: {active_strategies}</div>
                                <div>Confluence: {total_confluence}</div>
                                <div>Price: ${df_tf.iloc[-1]['close']:.2f}</div>
                            </div>
                        """, unsafe_allow_html=True)

            # ZBAR Logs
            if show_zbar_logs and analysis_results['zbar_logs']:
                st.subheader("📊 ZBAR Analysis Logs")

                for log in analysis_results['zbar_logs'][-5:]:  # Show last 5 logs
                    st.markdown(f"""
                        <div class="zbar-log">
                            <strong>[{log['strategy']}]</strong> {log['timestamp']}<br>
                            Status: {log['status']} | Confluence: {log['confluence_score']}<br>
                            Signals: {log['signals_count']} | Session: {log['session']}<br>
                            Market Context: {json.dumps(log['market_context'], indent=2)}
                        </div>
                    """, unsafe_allow_html=True)

            # Export functionality
            st.subheader("💾 Export Analysis Results")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📄 Export ZBAR Logs"):
                    logs_json = json.dumps(analysis_results['zbar_logs'], indent=2, default=str)
                    st.download_button(
                        label="Download ZBAR Logs",
                        data=logs_json,
                        file_name=f"zanflow_v12_zbar_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

            with col2:
                if st.button("📊 Export Strategy Analysis"):
                    analysis_json = json.dumps(analysis_results, indent=2, default=str)
                    st.download_button(
                        label="Download Analysis",
                        data=analysis_json,
                        file_name=f"zanflow_v12_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

            with col3:
                if st.button("📈 Export Enhanced Data"):
                    csv_data = current_df.to_csv()
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"zanflow_v12_data_{selected_symbol}_{selected_timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 2rem; color: #888;">
            <p><strong>🏛️ ZANFLOW v12 - Strategy-Based Trading Dashboard</strong></p>
            <p>SMC Liquidity Sweep • Wyckoff Accumulation • Session Judas Swing</p>
            <p>INSTITUTIONAL GRADE STRATEGY IMPLEMENTATION</p>
            <p><em>Built for professional traders and institutional analysis</em></p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()