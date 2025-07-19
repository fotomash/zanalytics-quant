#!/usr/bin/env python3
"""
Wyckoff Analysis Dashboard v3.0 - QRT Professional Level
Advanced Wyckoff Method Implementation with VSA and Market Structure Analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
from pathlib import Path
from datetime import datetime, timedelta, date
import warnings
from typing import Dict, List, Tuple, Optional
import logging
# --- PATCH: Wyckoff JSON Support ---
import json
from pathlib import Path
# --- PATCH: Wyckoff JSON Support ---

# ============================================================================
# PAGE CONFIGURATION (set_page_config must be called before any Streamlit code)
# ============================================================================
st.set_page_config(
    page_title="Wyckoff VSA Analysis - QRT Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PATCH: Add background image and set page width before Streamlit UI logic ---
import base64

def get_image_as_base64(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Background image not found at '{path}'")
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

st.markdown("""
<style>
.main .block-container {
    max-width: 998px !important;
    padding-left: 1.5vw;
    padding-right: 1.5vw;
}
</style>
""", unsafe_allow_html=True)
def load_comprehensive_json(symbol):
    json_path = Path(f"./processed/{symbol}_comprehensive.json")
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                content = f.read()
                if content.strip():
                    return json.loads(content)
                else:
                    st.warning(f"Comprehensive JSON file '{json_path}' is empty.")
                    return None
        except Exception as e:
            st.warning(f"Could not parse comprehensive JSON: {e}")
            return None
    else:
        return None

# Configure warnings and logging
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIGURATION AND STYLING
# ============================================================================

def setup_page_config():
    """Apply custom CSS for QRT professional styling"""
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            background: linear-gradient(135deg, #1e1e2e 0%, #2a2d47 100%);
            color: #ffffff;
        }
        
        /* Professional header styling */
        .header-style {
            background: rgba(10, 10, 10, 0.8);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        x
        /* Metric cards styling */
        .metric-card {
            background: rgba(10, 10, 10, 0.2);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background: rgba(30, 30, 46, 0.95);
            backdrop-filter: blur(10px);
        }
        
        /* Chart container */
        .chart-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 1rem;
            margin: 1rem 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /* Alert styling */
        .wyckoff-alert {
            background: linear-gradient(45deg, #ff6b6b, #ee5a52);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-weight: 600;
        }
        
        /* Phase indicator */
        .phase-indicator {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            margin: 0.2rem;
        }
        
        .accumulation { background: #4ecdc4; color: #2c3e50; }
        .markup { background: #45b7d1; color: white; }
        .distribution { background: #f39c12; color: white; }
        .markdown { background: #e74c3c; color: white; }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# WYCKOFF ANALYSIS ENGINE
# ============================================================================

class WyckoffAnalyzer:
    """Advanced Wyckoff Method Analysis Engine"""

    def __init__(self):
        self.phases = ['Accumulation', 'Markup', 'Distribution', 'Markdown']
        self.events = {
            'PS': 'Preliminary Support',
            'SC': 'Selling Climax',
            'AR': 'Automatic Rally',
            'ST': 'Secondary Test',
            'BC': 'Buying Climax',
            'SOW': 'Sign of Weakness',
            'LPSY': 'Last Point of Supply',
            'UTAD': 'Upthrust After Distribution'
        }

    def analyze_data(self, df: pd.DataFrame) -> Dict:
        """Comprehensive Wyckoff analysis of price and volume data"""
        try:
            results = {
                'phases': self._identify_phases(df),
                'events': self._identify_events(df),
                'vsa_analysis': self._analyze_volume_spread(df),
                'effort_result': self._analyze_effort_vs_result(df),
                'supply_demand': self._analyze_supply_demand_zones(df),
                'trend_analysis': self._analyze_trend_structure(df),
                'composite_operator': self._analyze_composite_operator(df)
            }
            return results
        except Exception as e:
            logger.error(f"Error in Wyckoff analysis: {e}")
            return {}

    def _identify_phases(self, df: pd.DataFrame) -> List[Dict]:
        """Identify Wyckoff market phases"""
        phases = []

        if len(df) < 50:
            return phases

        # Calculate rolling volatility and volume metrics
        df['price_volatility'] = df['close'].rolling(20).std()
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['price_change'] = df['close'].pct_change()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Phase detection logic
        for i in range(50, len(df) - 10):
            window = df.iloc[i-20:i+10]

            # Accumulation: low volatility, high volume, sideways price
            if (window['price_volatility'].mean() < df['price_volatility'].quantile(0.3) and
                window['volume_ratio'].mean() > 1.2 and
                abs(window['price_change'].mean()) < 0.001):

                phases.append({
                    'phase': 'Accumulation',
                    'start_idx': i-10,
                    'end_idx': i+10,
                    'strength': window['volume_ratio'].mean(),
                    'price_level': window['close'].mean(),
                    'description': 'Smart money accumulation phase'
                })

            # Markup: Rising prices with good volume
            elif (window['close'].iloc[-1] > window['close'].iloc[0] * 1.02 and
                  window['volume_ratio'].mean() > 1.0):

                phases.append({
                    'phase': 'Markup',
                    'start_idx': i-5,
                    'end_idx': i+5,
                    'strength': (window['close'].iloc[-1] - window['close'].iloc[0]) / window['close'].iloc[0],
                    'price_level': window['close'].mean(),
                    'description': 'Markup phase - trend continuation'
                })

            # Distribution: high volatility, high volume, topping action
            elif (window['price_volatility'].mean() > df['price_volatility'].quantile(0.7) and
                  window['volume_ratio'].mean() > 1.3 and
                  window['high'].max() == df['high'].iloc[i-20:i+20].max()):

                phases.append({
                    'phase': 'Distribution',
                    'start_idx': i-10,
                    'end_idx': i+10,
                    'strength': window['volume_ratio'].mean(),
                    'price_level': window['close'].mean(),
                    'description': 'Distribution phase - smart money selling'
                })

        return phases[-20:]  # Return last 20 phases to avoid overcrowding

    def _identify_events(self, df: pd.DataFrame) -> List[Dict]:
        """Identify specific Wyckoff events"""
        events = []

        df['volume_spike'] = df['volume'] > df['volume'].rolling(20).mean() * 2
        df['price_range'] = df['high'] - df['low']
        df['close_position'] = (df['close'] - df['low']) / df['price_range']

        for i in range(20, len(df)):
            # Selling Climax (SC)
            if (df.iloc[i]['volume_spike'] and
                df.iloc[i]['close'] < df.iloc[i-1]['close'] and
                df.iloc[i]['close_position'] < 0.3):

                events.append({
                    'event': 'SC',
                    'index': i,
                    'price': df.iloc[i]['close'],
                    'volume': df.iloc[i]['volume'],
                    'description': 'Selling Climax - Panic selling',
                    'significance': 'high'
                })

            # Buying Climax (BC)
            elif (df.iloc[i]['volume_spike'] and
                  df.iloc[i]['close'] > df.iloc[i-1]['close'] and
                  df.iloc[i]['close_position'] > 0.7):

                events.append({
                    'event': 'BC',
                    'index': i,
                    'price': df.iloc[i]['close'],
                    'volume': df.iloc[i]['volume'],
                    'description': 'Buying Climax - Exhaustion buying',
                    'significance': 'high'
                })

            # Automatic Rally (AR)
            elif (i > 0 and
                  df.iloc[i]['close'] > df.iloc[i-5:i]['close'].max() and
                  df.iloc[i]['volume'] > df.iloc[i-10:i]['volume'].mean()):

                events.append({
                    'event': 'AR',
                    'index': i,
                    'price': df.iloc[i]['close'],
                    'volume': df.iloc[i]['volume'],
                    'description': 'Automatic Rally - Relief bounce',
                    'significance': 'Medium'
                })

        return events[-30:]  # Return last 30 events

    def _analyze_volume_spread(self, df: pd.DataFrame) -> Dict:
        """volume Spread Analysis (VSA)"""
        df['spread'] = df['high'] - df['low']
        df['volume_norm'] = (df['volume'] - df['volume'].rolling(50).mean()) / df['volume'].rolling(50).std()
        df['spread_norm'] = (df['spread'] - df['spread'].rolling(50).mean()) / df['spread'].rolling(50).std()

        # VSA classifications
        conditions = []

        # high volume, narrow spread = absorption
        high_vol_narrow = (df['volume_norm'] > 1.5) & (df['spread_norm'] < -0.5)
        conditions.append(('Absorption', high_vol_narrow))

        # high volume, wide spread = professional activity
        high_vol_wide = (df['volume_norm'] > 1.5) & (df['spread_norm'] > 1.5)
        conditions.append(('Professional Activity', high_vol_wide))

        # low volume, wide spread = weak move
        low_vol_wide = (df['volume_norm'] < -0.5) & (df['spread_norm'] > 1.0)
        conditions.append(('Weak Move', low_vol_wide))

        # high volume, high close = strength
        high_vol_high_close = (df['volume_norm'] > 1.0) & ((df['close'] - df['low']) / df['spread'] > 0.7)
        conditions.append(('Strength', high_vol_high_close))

        vsa_signals = {}
        for name, condition in conditions:
            vsa_signals[name] = df.index[condition].tolist()

        return {
            'signals': vsa_signals,
            'volume_analysis': {
                'avg_volume': df['volume'].mean(),
                'volume_trend': df['volume'].rolling(50).mean().iloc[-1] / df['volume'].rolling(50).mean().iloc[-50] - 1,
                'high_volume_days': len(df[df['volume_norm'] > 2])
            }
        }

    def _analyze_effort_vs_result(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze effort (volume) vs result (price movement)"""
        analysis = []

        df['price_move'] = abs(df['close'] - df['open']) / df['open']
        df['volume_effort'] = df['volume'] / df['volume'].rolling(20).mean()

        for i in range(20, len(df)):
            effort = df.iloc[i]['volume_effort']
            result = df.iloc[i]['price_move']

            if effort > 2.0:  # high effort
                if result < 0.005:  # low result
                    analysis.append({
                        'index': i,
                        'type': 'high Effort, low Result',
                        'effort': effort,
                        'result': result,
                        'interpretation': 'Potential accumulation/distribution',
                        'significance': 'high'
                    })
                elif result > 0.02:  # high result
                    analysis.append({
                        'index': i,
                        'type': 'high Effort, high Result',
                        'effort': effort,
                        'result': result,
                        'interpretation': 'Strong directional move',
                        'significance': 'Medium'
                    })

        return analysis[-15:]  # Return last 15 analyses

    def _analyze_supply_demand_zones(self, df: pd.DataFrame) -> Dict:
        """Identify supply and demand zones"""
        supply_zones = []
        demand_zones = []

        # Find significant highs and lows with volume
        for i in range(10, len(df) - 10):
            window_high = df['high'].iloc[i-10:i+10].max()
            window_low = df['low'].iloc[i-10:i+10].min()
            volume_avg = df['volume'].iloc[i-10:i+10].mean()

            # Supply zone at significant high
            if (df.iloc[i]['high'] == window_high and
                df.iloc[i]['volume'] > volume_avg * 1.5):
                supply_zones.append({
                    'price': df.iloc[i]['high'],
                    'index': i,
                    'strength': df.iloc[i]['volume'] / volume_avg,
                    'type': 'Supply'
                })

            # Demand zone at significant low
            if (df.iloc[i]['low'] == window_low and
                df.iloc[i]['volume'] > volume_avg * 1.5):
                demand_zones.append({
                    'price': df.iloc[i]['low'],
                    'index': i,
                    'strength': df.iloc[i]['volume'] / volume_avg,
                    'type': 'Demand'
                })

        return {
            'supply_zones': supply_zones[-10:],
            'demand_zones': demand_zones[-10:],
            'current_bias': self._determine_current_bias(df)
        }

    def _analyze_trend_structure(self, df: pd.DataFrame) -> Dict:
        """Analyze market structure and trend"""
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(5, len(df) - 5):
            if df['high'].iloc[i] == df['high'].iloc[i-5:i+5].max():
                swing_highs.append({'index': i, 'price': df['high'].iloc[i]})
            if df['low'].iloc[i] == df['low'].iloc[i-5:i+5].min():
                swing_lows.append({'index': i, 'price': df['low'].iloc[i]})

        # Determine trend
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            recent_highs = swing_highs[-2:]
            recent_lows = swing_lows[-2:]

            if (recent_highs[1]['price'] > recent_highs[0]['price'] and
                recent_lows[1]['price'] > recent_lows[0]['price']):
                trend = 'Uptrend'
            elif (recent_highs[1]['price'] < recent_highs[0]['price'] and
                  recent_lows[1]['price'] < recent_lows[0]['price']):
                trend = 'Downtrend'
            else:
                trend = 'Sideways'
        else:
            trend = 'Insufficient Data'

        return {
            'trend': trend,
            'swing_highs': swing_highs[-5:],
            'swing_lows': swing_lows[-5:],
            'structure_breaks': self._find_structure_breaks(swing_highs, swing_lows)
        }

    def _analyze_composite_operator(self, df: pd.DataFrame) -> Dict:
        """Analyze Composite Operator behavior"""
        # This represents the collective actions of large institutional players
        co_analysis = {
            'accumulation_score': 0,
            'distribution_score': 0,
            'manipulation_events': [],
            'institutional_activity': 'Neutral'
        }

        # Look for signs of institutional accumulation/distribution
        df['volume_ma_50'] = df['volume'].rolling(50).mean()
        df['price_efficiency'] = abs(df['close'] - df['open']) / (df['high'] - df['low'])

        accumulation_signals = 0
        distribution_signals = 0

        for i in range(50, len(df)):
            # high volume, low price movement = potential accumulation
            if (df.iloc[i]['volume'] > df.iloc[i]['volume_ma_50'] * 1.5 and
                abs(df.iloc[i]['close'] - df.iloc[i]['open']) / df.iloc[i]['open'] < 0.01):
                accumulation_signals += 1

            # high volume at highs = potential distribution
            if (df.iloc[i]['volume'] > df.iloc[i]['volume_ma_50'] * 1.5 and
                df.iloc[i]['close'] < df.iloc[i]['high'] * 0.95 and
                df.iloc[i]['high'] == df['high'].iloc[i-10:i+1].max()):
                distribution_signals += 1

        co_analysis['accumulation_score'] = accumulation_signals / len(df) * 100
        co_analysis['distribution_score'] = distribution_signals / len(df) * 100

        if co_analysis['accumulation_score'] > co_analysis['distribution_score'] * 1.5:
            co_analysis['institutional_activity'] = 'Accumulating'
        elif co_analysis['distribution_score'] > co_analysis['accumulation_score'] * 1.5:
            co_analysis['institutional_activity'] = 'Distributing'

        return co_analysis

    def _determine_current_bias(self, df: pd.DataFrame) -> str:
        """Determine current market bias"""
        recent_data = df.tail(20)

        volume_trend = recent_data['volume'].rolling(10).mean().iloc[-1] / recent_data['volume'].rolling(10).mean().iloc[0]
        price_trend = recent_data['close'].iloc[-1] / recent_data['close'].iloc[0]

        if price_trend > 1.02 and volume_trend > 1.1:
            return 'Bullish with volume Support'
        elif price_trend < 0.98 and volume_trend > 1.1:
            return 'Bearish with volume Support'
        elif volume_trend < 0.9:
            return 'low volume - Caution'
        else:
            return 'Neutral'

    def _find_structure_breaks(self, swing_highs: List, swing_lows: List) -> List:
        """Find market structure breaks"""
        breaks = []
        # Implementation for structure break detection
        return breaks

# ============================================================================
# CHART CREATION FUNCTIONS
# ============================================================================

def create_wyckoff_chart(df: pd.DataFrame, analysis: Dict, symbol: str) -> go.Figure:
    """Create comprehensive Wyckoff analysis chart"""

    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=(
            f'{symbol} - Wyckoff Phase Analysis',
            'volume Analysis',
            'VSA Signals',
            'Effort vs Result'
        ),
        row_heights=[0.5, 0.2, 0.15, 0.15]
    )

    # Main price chart with candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
            increasing_fillcolor='rgba(38, 166, 154, 0.8)',
            decreasing_fillcolor='rgba(239, 83, 80, 0.8)'
        ),
        row=1, col=1
    )

    # Add Wyckoff phases
    if 'phases' in analysis:
        phase_colors = {
            'Accumulation': 'rgba(76, 175, 80, 0.3)',
            'Markup': 'rgba(33, 150, 243, 0.3)',
            'Distribution': 'rgba(255, 152, 0, 0.3)',
            'Markdown': 'rgba(244, 67, 54, 0.3)'
        }

        for phase in analysis['phases']:
            start_idx = phase['start_idx']
            end_idx = phase['end_idx']
            phase_name = phase['phase']

            if start_idx < len(df) and end_idx < len(df):
                fig.add_shape(
                    type="rect",
                    x0=df.index[start_idx],
                    x1=df.index[end_idx],
                    y0=df['low'].iloc[start_idx:end_idx+1].min(),
                    y1=df['high'].iloc[start_idx:end_idx+1].max(),
                    fillcolor=phase_colors.get(phase_name, 'rgba(128, 128, 128, 0.3)'),
                    line=dict(color=phase_colors.get(phase_name, 'gray'), width=2),
                    row=1, col=1
                )

                # Add phase label
                fig.add_annotation(
                    x=df.index[start_idx + (end_idx - start_idx) // 2],
                    y=df['high'].iloc[start_idx:end_idx+1].max(),
                    text=f"{phase_name}<br>Strength: {phase['strength']:.2f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=phase_colors.get(phase_name, 'gray'),
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor=phase_colors.get(phase_name, 'gray'),
                    font=dict(size=10),
                    row=1, col=1
                )

    # Add Wyckoff events
    if 'events' in analysis:
        event_colors = {
            'SC': '#f44336',  # Red
            'BC': '#ff9800',  # Orange
            'AR': '#4caf50',  # Green
            'ST': '#2196f3',  # Blue
            'PS': '#9c27b0'   # Purple
        }

        for event in analysis['events']:
            if event['index'] < len(df):
                color = event_colors.get(event['event'], '#666666')
                fig.add_trace(
                    go.Scatter(
                        x=[df.index[event['index']]],
                        y=[event['price']],
                        mode='markers',
                        marker=dict(
                            symbol='diamond',
                            size=15,
                            color=color,
                            line=dict(color='white', width=2)
                        ),
                        name=f"{event['event']} - {event['description']}",
                        hovertemplate=f"<b>{event['event']}</b><br>" +
                                    f"Price: ${event['price']:.2f}<br>" +
                                    f"volume: {event['volume']:,.0f}<br>" +
                                    f"Description: {event['description']}<br>" +
                                    f"Significance: {event['significance']}<extra></extra>",
                        showlegend=False
                    ),
                    row=1, col=1
                )

    # volume chart with color coding
    volume_colors = ['red' if close < open_price else 'green'
                    for close, open_price in zip(df['close'], df['open'])]

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='volume',
            marker_color=volume_colors,
            opacity=0.7,
            hovertemplate="volume: %{y:,.0f}<br>Date: %{x}<extra></extra>"
        ),
        row=2, col=1
    )

    # volume moving average
    df['volume_ma'] = df['volume'].rolling(20).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['volume_ma'],
            mode='lines',
            name='volume MA(20)',
            line=dict(color='yellow', width=2),
            hovertemplate="volume MA: %{y:,.0f}<extra></extra>"
        ),
        row=2, col=1
    )

    # VSA signals
    if 'vsa_analysis' in analysis:
        vsa_signals = analysis['vsa_analysis']['signals']

        signal_colors = {
            'Absorption': '#ff6b6b',
            'Professional Activity': '#4ecdc4',
            'Weak Move': '#ffe66d',
            'Strength': '#95e1d3'
        }

        for signal_type, indices in vsa_signals.items():
            if indices:
                signal_prices = [df['close'].iloc[i] for i in indices if i < len(df)]
                signal_dates = [df.index[i] for i in indices if i < len(df)]

                fig.add_trace(
                    go.Scatter(
                        x=signal_dates,
                        y=signal_prices,
                        mode='markers',
                        marker=dict(
                            symbol='circle',
                            size=8,
                            color=signal_colors.get(signal_type, '#666666')
                        ),
                        name=signal_type,
                        hovertemplate=f"<b>{signal_type}</b><br>" +
                                    "Price: $%{y:.2f}<br>" +
                                    "Date: %{x}<extra></extra>"
                    ),
                    row=3, col=1
                )

    # Effort vs Result analysis
    if 'effort_result' in analysis:
        effort_data = analysis['effort_result']

        for analysis_point in effort_data:
            if analysis_point['index'] < len(df):
                color = '#ff4757' if 'low Result' in analysis_point['type'] else '#2ed573'

                fig.add_trace(
                    go.Scatter(
                        x=[df.index[analysis_point['index']]],
                        y=[analysis_point['effort']],
                        mode='markers',
                        marker=dict(
                            symbol='square',
                            size=10,
                            color=color,
                            line=dict(color='white', width=1)
                        ),
                        name=analysis_point['type'],
                        hovertemplate=f"<b>{analysis_point['type']}</b><br>" +
                                    f"Effort: {analysis_point['effort']:.2f}<br>" +
                                    f"Result: {analysis_point['result']:.3f}<br>" +
                                    f"Interpretation: {analysis_point['interpretation']}<extra></extra>",
                        showlegend=False
                    ),
                    row=4, col=1
                )

    # Update layout with professional styling
    fig.update_layout(
        title=dict(
            text=f"Wyckoff VSA Analysis - {symbol}",
            font=dict(size=24, color='white'),
            x=0.5
        ),
        template='plotly_dark',
        height=900,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        font=dict(color='white'),
        paper_bgcolor='rgba(30, 30, 46, 0.95)',
        plot_bgcolor='rgba(30, 30, 46, 0.95)'
    )

    # Update axes
    fig.update_yaxes(title_text="Price ($)", row=1, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="volume", row=2, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="VSA Signals", row=3, col=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="Effort Ratio", row=4, col=1, gridcolor='rgba(255,255,255,0.1)')

    fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)')

    return fig

def create_phase_distribution_chart(analysis: Dict) -> go.Figure:
    """Create phase distribution chart"""
    if 'phases' not in analysis or not analysis['phases']:
        return go.Figure()

    phase_counts = {}
    for phase in analysis['phases']:
        phase_name = phase['phase']
        phase_counts[phase_name] = phase_counts.get(phase_name, 0) + 1

    fig = go.Figure(data=[
        go.Pie(
            labels=list(phase_counts.keys()),
            values=list(phase_counts.values()),
            hole=0.4,
            marker_colors=['#4ecdc4', '#45b7d1', '#f39c12', '#e74c3c'],
            hovertemplate="<b>%{label}</b><br>" +
                         "Count: %{value}<br>" +
                         "Percentage: %{percent}<extra></extra>"
        )
    ])

    fig.update_layout(
        title="Wyckoff Phase Distribution",
        template='plotly_dark',
        font=dict(color='white'),
        paper_bgcolor='rgba(30, 30, 46, 0.95)',
        height=400
    )

    return fig

def create_composite_operator_gauge(analysis: Dict) -> go.Figure:
    """Create Composite Operator activity gauge"""
    if 'composite_operator' not in analysis:
        return go.Figure()

    co_data = analysis['composite_operator']
    activity = co_data.get('institutional_activity', 'Neutral')

    # Determine gauge value and color
    if activity == 'Accumulating':
        value = 75
        color = '#4caf50'
    elif activity == 'Distributing':
        value = 25
        color = '#f44336'
    else:
        value = 50
        color = '#ff9800'

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Composite Operator Activity"},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': "lightgray"},
                {'range': [30, 70], 'color': "gray"},
                {'range': [70, 100], 'color': "lightgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(
        template='plotly_dark',
        font=dict(color='white', size=16),
        paper_bgcolor='rgba(30, 30, 46, 0.95)',
        height=300
    )

    return fig

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


# ============================================================================
# PARQUET DATA LOADER AND DIRECTORY UTILS
# ============================================================================

# Reference the parquet data directory from TOML/Streamlit secrets (set as PARQUET_DATA_DIR in secrets.toml)
DATA_DIR = st.secrets.get("PARQUET_DATA_DIR", "./data")

def list_parquet_files(data_dir):
    p = Path(data_dir)
    # Recursively find Parquet files one level down: SYMBOL/SYMBOL_1d.parquet etc
    return [f for f in p.glob("*/*.parquet") if f.is_file()]

@st.cache_data(ttl=300)
def load_parquet_data(data_dir, rel_path):
    file_path = Path(data_dir) / rel_path
    try:
        df = pd.read_parquet(file_path)
        return df
    except Exception as e:
        st.error(f"Error loading Parquet file: {e}")
        return pd.DataFrame()

def export_analysis_report(analysis: Dict, symbol: str) -> str:
    """Export analysis as JSON report"""
    report = {
        'symbol': symbol,
        'timestamp': datetime.now().isoformat(),
        'analysis': analysis
    }
    return json.dumps(report, indent=2, default=str)

# --- PATCH: Render trade setups from JSON or CSV ---
def render_trade_setups(symbol, json_data):
    if json_data and "trade_setups" in json_data:
        setups_iter = json_data["trade_setups"]
    else:
        try:
            setup_path = f"./processed/{symbol}_trade_setups.csv"
            setups_iter = pd.read_csv(setup_path).to_dict('records')
        except Exception as e:
            st.warning(f"No trade-setup data found: {e}")
            setups_iter = []

    for setup in setups_iter:
        targets_raw = setup.get("targets") or setup.get("Targets", "")
        if isinstance(targets_raw, str):
            targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        else:
            targets = targets_raw
        card = {
            "name":        setup.get("name")        or setup.get("Name", "Unnamed"),
            "entry":       setup.get("entry")       or setup.get("Entry", "—"),
            "stop":        setup.get("stop")        or setup.get("Stop", "—"),
            "targets":     targets,
            "rr":          setup.get("rr")          or setup.get("RR", "—"),
            "confidence":  setup.get("confidence")  or setup.get("Confidence", "—"),
            "status":      setup.get("status")      or setup.get("Status", "Pending"),
            "color":       setup.get("color",       "#ffc13b")
        }
        # Render in a visually distinct card
        with st.container():
            st.markdown(
                f"<div style='border-left:8px solid {card['color']};padding:0.7em 1em;margin:0.5em 0;background:rgba(80,80,80,0.1);border-radius:8px'>"
                f"<b>{card['name']}</b> | <b>Entry:</b> {card['entry']} | <b>Stop:</b> {card['stop']} | "
                f"<b>Targets:</b> {', '.join(card['targets']) if card['targets'] else '—'} | "
                f"<b>RR:</b> {card['rr']} | <b>Confidence:</b> {card['confidence']} | "
                f"<b>Status:</b> {card['status']}"
                f"</div>", unsafe_allow_html=True
            )

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application"""

    # Setup page configuration
    setup_page_config()

    # Parquet data directory info
    st.markdown("""
    **Note:** Parquet data directory is set in `.streamlit/secrets.toml` as `PARQUET_DATA_DIR`.
    Update this key to change the file source.
    """)

    # Professional header
    st.markdown("""
        <div class="header-style">
            <h1>📊 Wyckoff VSA Analysis Dashboard</h1>
            <p><strong>Professional volume Spread Analysis & Market Structure</strong></p>
            <p>QRT-Level Advanced Trading Analytics</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar controls
    with st.sidebar:
        st.header("🗂️ Data Selection")
        parquet_files = list_parquet_files(DATA_DIR)
        relative_files = [f.relative_to(DATA_DIR) for f in parquet_files]

        # Extract symbols and timeframes from filenames
        file_info = []
        for f in relative_files:
            parts = f.stem.split("_")
            if len(parts) >= 2:
                symbol = parts[0]
                tf = parts[1]
                file_info.append((symbol, tf, f))

        symbols = sorted(set([s for s, _, _ in file_info]))
        if not symbols:
            st.warning("No symbols found in the data directory.")
            st.stop()
        selected_symbol = st.selectbox("Select Symbol", symbols)

        timeframes = sorted(set([tf for s, tf, _ in file_info if s == selected_symbol]))
        if not timeframes:
            st.warning("No timeframes found for the selected symbol.")
            st.stop()
        selected_tf = st.selectbox("Select Timeframe", timeframes)

        # Find the matching file
        try:
            selected_file = next(f for s, tf, f in file_info if s == selected_symbol and tf == selected_tf)
            selected_file = str(selected_file)  # convert Path to string
        except StopIteration:
            st.warning("No file found for the selected symbol and timeframe.")
            st.stop()

        # Insert Last N Bars slider before Analysis Options and Advanced Settings
        max_bars = len(pd.read_parquet(Path(DATA_DIR) / selected_file))
        bars_to_use = st.slider("Last N Bars to Analyze", min_value=20, max_value=max_bars, value=min(500, max_bars), step=10)

        # Analysis options as before
        st.subheader("Analysis Options")
        show_phases = st.checkbox("Show Wyckoff Phases", value=True)
        show_events = st.checkbox("Show Wyckoff Events", value=True)
        show_vsa = st.checkbox("Show VSA Signals", value=True)
        show_effort_result = st.checkbox("Show Effort vs Result", value=True)
        with st.expander("Advanced Settings"):
            volume_threshold = st.slider("volume Spike Threshold", 1.5, 3.0, 2.0, 0.1)
            volatility_threshold = st.slider("Volatility Threshold", 0.2, 1.0, 0.3, 0.1)
            phase_sensitivity = st.slider("Phase Detection Sensitivity", 0.5, 2.0, 1.0, 0.1)

    # --- PATCH: Try to load enriched JSON for the selected symbol ---
    comprehensive_json = load_comprehensive_json(selected_symbol)

    # Main content area
    if st.button("🚀 Run Analysis", type="primary"):
        with st.spinner("Loading market data and performing analysis..."):
            # Load data from Parquet using the relative path
            df = load_parquet_data(DATA_DIR, selected_file)
            df = df.tail(bars_to_use)
            if df.empty:
                st.error("Unable to load data from the selected Parquet file.")
                return

            # Use relative path as symbol label
            symbol = selected_file

            # Perform Wyckoff analysis
            analyzer = WyckoffAnalyzer()
            analysis = analyzer.analyze_data(df)

            if not analysis:
                st.error("Analysis failed. Please try again.")
                return

            # Display key metrics
            st.subheader("📈 Key Metrics")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                current_price = df['close'].iloc[-1]
                price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                st.metric(
                    "Current Price",
                    f"${current_price:.2f}",
                    f"{price_change:+.2f}%"
                )

            with col2:
                avg_volume = df['volume'].mean()
                recent_volume = df['volume'].iloc[-5:].mean()
                volume_change = ((recent_volume - avg_volume) / avg_volume) * 100
                st.metric(
                    "Avg volume",
                    f"{avg_volume:,.0f}",
                    f"{volume_change:+.1f}%"
                )

            with col3:
                if 'trend_analysis' in analysis:
                    trend = analysis['trend_analysis']['trend']
                    st.metric("Market Trend", trend)
                else:
                    st.metric("Market Trend", "N/A")

            with col4:
                if 'composite_operator' in analysis:
                    co_activity = analysis['composite_operator']['institutional_activity']
                    st.metric("Institutional Activity", co_activity)
                else:
                    st.metric("Institutional Activity", "N/A")

            # Main analysis chart
            st.subheader("📊 Wyckoff Analysis Chart")
            main_chart = create_wyckoff_chart(df, analysis, symbol)
            st.plotly_chart(main_chart, use_container_width=True)

            # Secondary charts
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Phase Distribution")
                phase_chart = create_phase_distribution_chart(analysis)
                st.plotly_chart(phase_chart, use_container_width=True)

            with col2:
                st.subheader("🎯 Composite Operator")
                co_gauge = create_composite_operator_gauge(analysis)
                st.plotly_chart(co_gauge, use_container_width=True)

            # --- PATCH: Show trade setups from JSON/CSV ---
            st.subheader("📑 Trade Setups")
            render_trade_setups(selected_symbol, comprehensive_json)

            # Detailed analysis results
            st.subheader("📋 Detailed Analysis")

            # Wyckoff Events
            if 'events' in analysis and analysis['events']:
                with st.expander("🎯 Wyckoff Events"):
                    events_df = pd.DataFrame(analysis['events'])
                    st.dataframe(events_df, use_container_width=True)

            # VSA Analysis
            if 'vsa_analysis' in analysis:
                with st.expander("📊 volume Spread Analysis"):
                    vsa_data = analysis['vsa_analysis']
                    st.write("**volume Analysis:**")
                    for key, value in vsa_data['volume_analysis'].items():
                        if isinstance(value, float):
                            st.write(f"- {key.replace('_', ' ').title()}: {value:.2f}")
                        else:
                            st.write(f"- {key.replace('_', ' ').title()}: {value}")
                    st.write("**VSA Signals:**")
                    for signal_type, indices in vsa_data['signals'].items():
                        st.write(f"- {signal_type}: {len(indices)} occurrences")

            # Effort vs Result
            if 'effort_result' in analysis and analysis['effort_result']:
                with st.expander("⚖️ Effort vs Result Analysis"):
                    effort_df = pd.DataFrame(analysis['effort_result'])
                    st.dataframe(effort_df, use_container_width=True)

            # Supply & Demand Zones
            if 'supply_demand' in analysis:
                with st.expander("🎯 Supply & Demand Zones"):
                    sd_data = analysis['supply_demand']
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Supply Zones:**")
                        if sd_data['supply_zones']:
                            supply_df = pd.DataFrame(sd_data['supply_zones'])
                            st.dataframe(supply_df, use_container_width=True)
                        else:
                            st.write("No significant supply zones detected")
                    with col2:
                        st.write("**Demand Zones:**")
                        if sd_data['demand_zones']:
                            demand_df = pd.DataFrame(sd_data['demand_zones'])
                            st.dataframe(demand_df, use_container_width=True)
                        else:
                            st.write("No significant demand zones detected")
                    st.write(f"**Current Market Bias:** {sd_data['current_bias']}")

            # Export functionality
            st.subheader("💾 Export Analysis")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Export JSON Report"):
                    report = export_analysis_report(analysis, symbol)
                    st.download_button(
                        label="Download Report",
                        data=report,
                        file_name=f"wyckoff_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            with col2:
                if st.button("📊 Export Chart Data"):
                    csv_data = df.to_csv()
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"market_data_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; padding: 1rem; color: #888;">
            <p><strong>Wyckoff VSA Analysis Dashboard v3.0</strong></p>
            <p>Professional-grade market analysis for institutional traders</p>
            <p>Built with advanced volume Spread Analysis and Wyckoff Method principles</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()