
import streamlit as st

# ==== Unified Chart Styling Constants ====
CHART_THEME = "plotly_dark"
CANDLE_UP_COLOR = "lime"
CANDLE_DOWN_COLOR = "red"
FVG_BULL_COLOR = "rgba(0,255,0,0.13)"
FVG_BEAR_COLOR = "rgba(255,0,0,0.13)"
WYCKOFF_ACCUM_COLOR = "rgba(0,90,255,0.08)"
WYCKOFF_MARKUP_COLOR = "rgba(0,200,70,0.08)"
WYCKOFF_DIST_COLOR = "rgba(255,160,0,0.08)"
WYCKOFF_MARKDOWN_COLOR = "rgba(220,40,40,0.08)"
CHART_BG_COLOR = "rgba(0,0,0,0.02)"
CHART_FONT_COLOR = "white"
CHART_MARGIN = dict(l=20, r=20, t=40, b=20)
# Helper to apply to any Plotly fig
def apply_dashboard_style(fig, title=None, height=460):
    fig.update_layout(
        template=CHART_THEME,
        height=height,
        autosize=True,
        paper_bgcolor=CHART_BG_COLOR,
        plot_bgcolor=CHART_BG_COLOR,
        font=dict(color=CHART_FONT_COLOR),
        margin=CHART_MARGIN,
        showlegend=False,
    )
    if title is not None:
        fig.update_layout(
            title={
                "text": title,
                "y": 0.93,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top"
            }
        )
    return fig

st.set_page_config(
    page_title="Zanflow Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from streamlit_autorefresh import st_autorefresh

with open("custom_theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import warnings
import re
from pathlib import Path

warnings.filterwarnings('ignore')

from typing import Dict, Optional

# ========== Parquet File Scanning Utility ==========
def scan_parquet_files(parquet_dir):
    files = []
    for f in Path(parquet_dir).rglob("*.parquet"):
        name = f.stem.upper()
        parent = f.parent.name.upper()
        # First: Try SYMBOL_TIMEFRAME format in filename
        m = re.match(r"(.+)_([0-9]+[A-Z]+)$", name, re.IGNORECASE)
        if m:
            symbol, timeframe = m.group(1).upper(), m.group(2).upper()
        # Second: If filename looks like timeframe, parent is symbol
        elif re.match(r"\d+[A-Z]+", name):
            symbol = parent
            timeframe = name
        # Third: If folder looks like timeframe, filename is symbol
        elif re.match(r"\d+[A-Z]+", parent):
            symbol = name
            timeframe = parent
        else:
            continue
        files.append((symbol, timeframe, f.relative_to(parquet_dir)))
    return files

try:
    from utils.quantum_microstructure_analyzer import QuantumMicrostructureAnalyzer
except ImportError:
    # Fallback stub so the dashboard can still run if the full library isn't available.
    class QuantumMicrostructureAnalyzer:
        def __init__(self, config_path: str):
            self.config_path = config_path
            self.session_state = {}

# Import custom modules
from utils.data_processor import DataProcessor
from utils.timeframe_converter import TimeframeConverter
from utils.technical_analysis import TechnicalAnalysis

try:
    from utils.smc_analyzer import SMCAnalyzer
except ImportError:
    # Graceful fallback if the module isn't available
    class SMCAnalyzer:
        def analyze(self, df):
            return {}
from utils.wyckoff_analyzer import WyckoffAnalyzer
from utils.volume_profile import VolumeProfileAnalyzer
from components.chart_builder import ChartBuilder
from components.analysis_panel import AnalysisPanel


# ===================== QRT‑LEVEL QUANTUM ANALYZER =====================
class QRTQuantumAnalyzer(QuantumMicrostructureAnalyzer):
    """QRT‑level quantum microstructure analyzer with advanced Wyckoff and liquidity analysis"""

    def __init__(self, config_path: str):
        super().__init__(config_path)
        self.tiquidity_engine = TiquidityEngine()
        self.wyckoff_analyzer = WyckoffQuantumAnalyzer()

    def calculate_tiquidity_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced tick liquidity metrics"""
        # --- Ensure required columns exist for higher‑timeframe data ---
        if 'price_mid' not in df.columns:
            df['price_mid'] = (df['high'] + df['low']) / 2

        # Make sure a 'timestamp' column exists for downstream calculations/plots
        if 'timestamp' not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                # copy to avoid SettingWithCopy issues and preserve original index
                df = df.copy()
                df['timestamp'] = df.index
            elif 'datetime' in df.columns:
                df['timestamp'] = pd.to_datetime(df['datetime'])
            elif 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'])
            elif 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'])
            else:
                raise KeyError(
                    "DataFrame must contain a datetime index or a 'timestamp'/'datetime'/'date' column "
                    "for QRT analytics."
                )

        # Ensure 'timestamp' is a proper pandas datetime (handles tick‑data strings like '2025.06.29 19:21:36')
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            if df['timestamp'].isna().all():
                raise ValueError("Failed to parse 'timestamp' column to datetime format.")

        # Provide a usable volume field for liquidity math
        if 'inferred_volume' not in df.columns:
            if 'real_volume' in df.columns and (df['real_volume'] > 0).any():
                df['inferred_volume'] = df['real_volume'].replace(0, np.nan).fillna(method='ffill').fillna(0)
            elif 'volume' in df.columns:
                df['inferred_volume'] = df['volume']
            else:
                df['inferred_volume'] = 1.0  # minimal placeholder

        # Fill missing OHLC columns with placeholder logic, prefer 'last' if present
        ohlc_cols = ['open', 'high', 'low', 'close']
        missing_ohlc = [col for col in ohlc_cols if col not in df.columns]
        if missing_ohlc:
            base_price = df['last'] if 'last' in df.columns else df['price_mid']
            df['open'] = base_price.shift().fillna(base_price)
            df['close'] = base_price
            df['high'] = pd.concat([df['open'], df['close']], axis=1).max(axis=1)
            df['low'] = pd.concat([df['open'], df['close']], axis=1).min(axis=1)

        # Cumulative Delta
        df['delta'] = (df['inferred_volume'] * np.where(df['price_mid'].diff() > 0, 1, -1))
        df['cumulative_delta'] = df['delta'].cumsum()

        # Delta Divergence
        df['price_norm'] = (df['price_mid'] - df['price_mid'].min()) / (df['price_mid'].max() - df['price_mid'].min())
        df['delta_norm'] = (df['cumulative_delta'] - df['cumulative_delta'].min()) / (
                    df['cumulative_delta'].max() - df['cumulative_delta'].min() + 1e-9)
        df['delta_divergence'] = df['price_norm'] - df['delta_norm']

        # Absorption Ratio
        df['absorption_ratio'] = df['inferred_volume'].rolling(20).sum() / (
                    abs(df['price_mid'].diff()).rolling(20).sum() + 1e-9)

        # Exhaustion Levels
        df['volume_ma'] = df['inferred_volume'].rolling(50).mean()
        df['exhaustion_score'] = pd.Series(
            np.where(
                (df['inferred_volume'] > df['volume_ma'] * 3) &
                (abs(df['price_mid'].diff()) < df['price_mid'].rolling(50).std() * 0.1),
                1, 0
            )
        ).rolling(10).sum().values

        # Liquidity Voids
        if 'tick_interval_ms' not in df.columns:
            # Approximate bar interval in milliseconds, robust to non-monotonic/duplicate timestamps
            df['tick_interval_ms'] = (
                df['timestamp'].diff()
                .dt.total_seconds()
                .abs()  # ensure positive
                .fillna(0)
                .mul(1000)
            )
        # Ensure .rolling() is only called on pandas Series, not numpy arrays
        # Robust: use pd.Series(df['tick_interval_ms']) to avoid accidental numpy
        df['tick_gap'] = pd.Series(df['tick_interval_ms']).rolling(10).max().values
        df['liquidity_void'] = np.where(df['tick_gap'] > df['tick_interval_ms'].mean() * 5, 1, 0)

        return df

    def detect_wyckoff_structures(self, df: pd.DataFrame) -> Dict:
        """Detect comprehensive Wyckoff patterns at QRT level"""
        patterns = {
            'accumulation': [],
            'distribution': [],
            'springs': [],
            'utads': [],
            'tests': [],
            'creek_jumps': []
        }

        # Volume profile for Wyckoff analysis
        df['volume_sma'] = df['inferred_volume'].rolling(50).mean()
        df['volume_ratio'] = df['inferred_volume'] / (df['volume_sma'] + 1e-9)

        # Detect Accumulation Structures
        for i in range(100, len(df) - 50):
            window = df.iloc[i - 100:i + 50]

            # Phase A - Selling Climax
            if self._detect_selling_climax(window[:50]):
                # Phase B - Building Cause
                if self._detect_accumulation_range(window[25:75]):
                    # Phase C - Spring
                    spring_idx = self._detect_spring(window[50:100])
                    if spring_idx is not None:
                        # Phase D - Markup
                        if self._detect_markup_beginning(window[75:]):
                            patterns['accumulation'].append({
                                'start': window.index[0],
                                'spring_time': window.index[50 + spring_idx],
                                'phase': 'complete',
                                'confidence': 0.85
                            })

        # Detect Micro‑Wyckoff Patterns (Tick Level)
        for i in range(20, len(df) - 10):
            micro_window = df.iloc[i - 10:i + 10]

            # Micro‑Spring Detection
            if (micro_window['price_mid'].iloc[10] < micro_window['price_mid'].iloc[:10].min() and
                    micro_window['price_mid'].iloc[-1] > micro_window['price_mid'].iloc[10] and
                    micro_window['volume_ratio'].iloc[10] > 2.5):
                velocity = (micro_window['price_mid'].iloc[-1] - micro_window['price_mid'].iloc[10]) / (
                            micro_window['tick_interval_ms'].iloc[10:].sum() + 1)

                patterns['springs'].append({
                    'type': 'micro_spring',
                    'timestamp': micro_window['timestamp'].iloc[10],
                    'low': micro_window['price_mid'].iloc[10],
                    'rejection_velocity': velocity,
                    'volume_surge': micro_window['volume_ratio'].iloc[10],
                    'delta_flip': micro_window['delta'].iloc[11:].sum(),
                    'confidence': min(velocity * 1000 * micro_window['volume_ratio'].iloc[10] / 3, 1.0)
                })

        return patterns

    def calculate_orderflow_footprint(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate order flow footprint for each price level"""
        df['price_level'] = (df['price_mid'] * 10000).round() / 10000

        footprint = df.groupby('price_level').agg({
            'inferred_volume': 'sum',
            'delta': 'sum',
            'timestamp': 'count'
        }).rename(columns={'timestamp': 'tick_count'})

        footprint['bid_volume'] = np.where(footprint['delta'] < 0, abs(footprint['delta']), 0)
        footprint['ask_volume'] = np.where(footprint['delta'] > 0, footprint['delta'], 0)
        footprint['imbalance'] = footprint['ask_volume'] - footprint['bid_volume']

        return footprint

    def detect_liquidity_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect advanced liquidity patterns"""
        patterns = {
            'absorption_zones': [],
            'liquidity_voids': [],
            'imbalance_zones': [],
            'delta_divergences': []
        }

        high_absorption = df[df['absorption_ratio'] > df['absorption_ratio'].quantile(0.9)]
        for idx in high_absorption.index:
            # Convert index label to integer position
            int_idx = df.index.get_loc(idx)
            pre_move = 0
            post_move = 0
            if int_idx - 10 >= 0 and int_idx + 10 < len(df):
                pre_prices = df.iloc[int_idx - 10:int_idx]['price_mid']
                post_prices = df.iloc[int_idx:int_idx + 10]['price_mid']
                if len(pre_prices) > 1:
                    pre_move = abs(pre_prices.pct_change().sum())
                if len(post_prices) > 1:
                    post_move = abs(post_prices.pct_change().sum())

            if pre_move > 0 and post_move < pre_move * 0.3:
                patterns['absorption_zones'].append({
                    'timestamp': df.loc[idx, 'timestamp'],
                    'price': df.loc[idx, 'price_mid'],
                    'absorption_ratio': df.loc[idx, 'absorption_ratio'],
                    'effectiveness': 1 - (post_move / (pre_move + 1e-9))
                })

        divergence_points = df[abs(df['delta_divergence']) > 0.3]
        for idx in divergence_points.index:
            patterns['delta_divergences'].append({
                'timestamp': df.loc[idx, 'timestamp'],
                'price': df.loc[idx, 'price_mid'],
                'divergence': df.loc[idx, 'delta_divergence'],
                'type': 'bullish' if df.loc[idx, 'delta_divergence'] < -0.3 else 'bearish'
            })

        return patterns

    def create_qrt_dashboard(self, df: pd.DataFrame, selected_file: str):
        """Create QRT-level professional dashboard with unified styling constants."""
        import base64
        import streamlit as st
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        # Calculate metrics and signals before the heading
        df = self.calculate_tiquidity_metrics(df)
        wyckoff = self.detect_wyckoff_structures(df)
        liquidity = self.detect_liquidity_patterns(df)
        footprint = self.calculate_orderflow_footprint(df)
        signals = self.generate_qrt_signals(df, wyckoff, liquidity)
        st.markdown(
            f"<h2>QRT Trading Signal: <span style='color:#FFD700'>{signals.get('signal', 'N/A').upper()}</span></h2>",
            unsafe_allow_html=True
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Last Price", f"${df['price_mid'].iloc[-1]:.5f}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Cumulative Delta", f"{df['cumulative_delta'].iloc[-1]:,.0f}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Absorption Ratio", f"{df['absorption_ratio'].iloc[-1]:.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Exhaustion Score", f"{df['exhaustion_score'].iloc[-1]:.2f}")
            st.markdown("</div>", unsafe_allow_html=True)

        # Chart
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3]
        )
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color=CANDLE_UP_COLOR,
            decreasing_line_color=CANDLE_DOWN_COLOR,
            line_width=1.5
        ), row=1, col=1)
        # Cumulative Delta (as line)
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['cumulative_delta'],
            name="Cumulative Delta",
            line=dict(color='orange', width=2.2),
            opacity=0.8,
        ), row=2, col=1)
        # Volume bar chart with robust auto-detection of usable volume column
        volume_candidates = [col for col in df.columns if 'vol' in col.lower() or 'volume' in col.lower()]
        volume_col = next((col for col in volume_candidates if col in df.columns and df[col].sum() > 0), None)
        if volume_col:
            fig.add_trace(go.Bar(
                x=df['timestamp'],
                y=df[volume_col],
                name=f"Volume ({volume_col})",
                marker_color='rgba(50,150,255,0.7)',
                marker_line_width=0.5,
                opacity=0.8,
            ), row=2, col=1)
        else:
            st.warning("⚠️ No usable volume column found in data.")
        # Apply unified chart style
        fig = apply_dashboard_style(fig, title="QRT Dashboard", height=600)
        st.plotly_chart(fig, use_container_width=True)
        # Wyckoff Patterns
        with st.expander("🔬 Wyckoff Pattern Detection"):
            st.write(wyckoff)
        # Liquidity Patterns
        with st.expander("💧 Liquidity Patterns"):
            st.write(liquidity)
        # Orderflow Footprint
        with st.expander("🦶 Orderflow Footprint"):
            st.dataframe(footprint.head(30))
        # QRT Trading Signal details (JSON, reasons, etc.) in expander
        with st.expander("🧠 QRT Trading Signal"):
            st.success(f"**QRT Trading Signal:** {signals.get('signal', 'N/A').upper()}")
            st.json(signals)

    def generate_qrt_signals(self, df: pd.DataFrame, wyckoff: Dict, liquidity: Dict) -> Dict:
        """Generate QRT-level trading signals"""
        # Signal logic: combine Wyckoff spring, absorption, and delta divergence
        signal = "neutral"
        reasons = []
        # Bullish: recent micro_spring + strong absorption + bullish delta divergence
        recent_springs = [s for s in wyckoff.get('springs', []) if s.get('confidence', 0) > 0.7]
        strong_abs = [a for a in liquidity.get('absorption_zones', []) if a.get('effectiveness', 0) > 0.5]
        bullish_div = [d for d in liquidity.get('delta_divergences', []) if d.get('type') == 'bullish']
        bearish_div = [d for d in liquidity.get('delta_divergences', []) if d.get('type') == 'bearish']
        if recent_springs and strong_abs and bullish_div:
            signal = "long"
            reasons.append("Micro spring, strong absorption, bullish delta divergence")
        elif bearish_div and not recent_springs and not strong_abs:
            signal = "short"
            reasons.append("Bearish delta divergence, no bullish absorption/spring")
        elif strong_abs:
            signal = "wait"
            reasons.append("Absorption but no clear reversal")
        else:
            signal = "neutral"
            reasons.append("No strong confluence")
        return {"signal": signal, "reasons": reasons, "springs": recent_springs, "absorption": strong_abs,
                "delta_div": bullish_div + bearish_div}

    def _detect_selling_climax(self, df):
        # TODO: Replace with real selling climax detection logic
        return False

    def _detect_accumulation_range(self, df):
        # TODO: Replace with real accumulation range detection logic
        return False

    def _detect_spring(self, df):
        # TODO: Replace with real spring detection logic
        return None

    def _detect_markup_beginning(self, df):
        # TODO: Replace with real markup beginning detection logic
        return False


class TiquidityEngine:
    """Engine for tick liquidity analysis"""
    pass


class WyckoffQuantumAnalyzer:
    """Advanced Wyckoff pattern analyzer"""

    def detect_phases(self, df: pd.DataFrame) -> Dict:
        """Detect Wyckoff phases using volume and price action heuristics"""
        phases = []
        # Simple example: If cumulative delta rising and volume increasing, markup
        if df['cumulative_delta'].iloc[-1] > df['cumulative_delta'].iloc[0] and \
                df['inferred_volume'].rolling(50).mean().iloc[-1] > df['inferred_volume'].rolling(50).mean().iloc[0]:
            phases.append('Markup')
        elif df['cumulative_delta'].iloc[-1] < df['cumulative_delta'].iloc[0]:
            phases.append('Distribution')
        else:
            phases.append('Accumulation')
        return {"phases": phases}

    def detect_events(self, df: pd.DataFrame) -> list:
        """Detect key Wyckoff events (SC, AR, ST, Spring, UTAD)"""
        events = []
        # Example: Spring = local min with high volume
        min_idx = df['price_mid'].idxmin()
        if df['inferred_volume'].iloc[min_idx] > df['inferred_volume'].rolling(50).mean().iloc[min_idx] * 2:
            events.append({"type": "Spring", "price": df['price_mid'].iloc[min_idx]})
        return events


# =================== END QRT ANALYZER DEFINITIONS =====================

# ============================ MAIN UI & LOGIC SECTION (REPLACEMENT) ============================

# Custom CSS for styling
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.2);
        padding: 5px 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- PATCH: Add background image logic after CSS and before UI logic ---
import base64

def get_image_as_base64(path):
    """Reads an image file and returns its base64 encoded string."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Background image not found at '{path}'. Please ensure it's in the same directory as the script.")
        return None

img_base64 = get_image_as_base64("theme/image_af247b.jpg")
if img_base64:
    background_style = f"""
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
    """
    st.markdown(background_style, unsafe_allow_html=True)
    # PATCH: Panel transparency to match Home.py (alpha 0.025)
    st.markdown("""
    <style>
    .main .block-container {
        background-color: rgba(0,0,0,0.025) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'df_to_use' not in st.session_state:
    st.session_state.df_to_use = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

# Header
st.markdown(
    "<small>Institutional-Grade Market Analysis with Smart Money Concepts & Wyckoff Methodology</small>",
    unsafe_allow_html=True
)

# Sidebar: Data Selection and Analysis Controls
with st.sidebar:
    st.header("📁 Data Selection")
    parquet_dir = st.secrets.get("PARQUET_DATA_DIR", "./data")
    file_info = scan_parquet_files(parquet_dir)
    symbols = sorted({sym for sym, _, _ in file_info})
    if not symbols:
        st.warning("No Parquet files found in data folder.")
        st.info("Please place your Parquet files in the configured directory.")
        st.session_state.df_to_use = None
    else:
        selected_symbol = st.selectbox("Select Symbol", symbols)
        timeframes = sorted({tf for sym, tf, _ in file_info if sym == selected_symbol})
        selected_timeframe = st.selectbox("Select Timeframe", timeframes)
        rel_path = next(f for sym, tf, f in file_info if sym == selected_symbol and tf == selected_timeframe)
        full_path = Path(parquet_dir) / rel_path
        try:
            df = pd.read_parquet(full_path)
            df.columns = [c.lower() for c in df.columns]

            # --- PATCH: Robust cleaning: convert price columns with commas to float, and sort by timestamp ascending ---
            for price_col in ['open', 'high', 'low', 'close']:
                if price_col in df.columns:
                    # Remove commas, convert to float (robust for e.g. "1,234.56")
                    df[price_col] = pd.to_numeric(df[price_col].astype(str).str.replace(",", ""), errors='coerce')

            if 'timestamp' in df.columns:
                df = df.sort_values('timestamp')

            # -- PATCH: Robust cleaning for 1-minute chart data --
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # --- FIX: handle numeric epoch timestamps (seconds vs milliseconds) ---
                if pd.api.types.is_numeric_dtype(df['timestamp']):
                    # If max value looks like milliseconds (> 1e12) treat as 'ms', else 's'
                    ts_max = df['timestamp'].max()
                    unit = 'ms' if ts_max > 1_000_000_000_000 else 's'
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit=unit, errors='coerce')
            elif 'datetime' in df.columns:
                df['timestamp'] = pd.to_datetime(df['datetime'], errors='coerce')
            elif 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'], errors='coerce')
            elif 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
            else:
                raise KeyError("No timestamp/datetime/date/time column found in data.")

            # Drop rows with missing timestamps
            df = df.dropna(subset=['timestamp'])

            # Remove duplicates: Only keep first occurrence of any timestamp (1-min chart must be unique per bar)
            df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])

            # Fill missing OHLC columns only if they don't exist
            ohlc_cols = ['open', 'high', 'low', 'close']
            missing_ohlc = [col for col in ohlc_cols if col not in df.columns]
            synthetic_bars = False
            if missing_ohlc:
                # Try to use 'last' or 'price_mid' as fallback for all missing OHLC fields
                base_price = df['last'] if 'last' in df.columns else df['price_mid'] if 'price_mid' in df.columns else None
                if base_price is not None:
                    if 'open' not in df.columns:
                        df['open'] = base_price.shift().fillna(base_price)
                    if 'close' not in df.columns:
                        df['close'] = base_price
                    if 'high' not in df.columns:
                        df['high'] = pd.concat([df['open'], df['close']], axis=1).max(axis=1)
                    if 'low' not in df.columns:
                        df['low'] = pd.concat([df['open'], df['close']], axis=1).min(axis=1)
                    synthetic_bars = True
                else:
                    raise ValueError("Cannot fill missing OHLC columns: no 'last' or 'price_mid' found.")

            # --- PATCH: Warn if bars are synthetic or appear to be synthetic ---
            if synthetic_bars:
                st.warning("⚠️ Synthetic bars detected: OHLC columns were missing and have been constructed from a single price column ('last' or 'price_mid'). These bars may not reflect real market data.")

            # Additional check: even if OHLC exists, warn if they are all (nearly) identical for the most recent bar(s)
            try:
                recent = df[['open', 'high', 'low', 'close']].tail(10)
                # Count how many unique values per row; if <=2, likely synthetic
                if (recent.nunique(axis=1) <= 2).any():
                    st.warning("⚠️ Many recent bars have identical or nearly identical OHLC values. This suggests your data source may not contain real OHLC candles. Results may not be reliable for candlestick analysis.")
            except Exception:
                pass

            # Force all price columns to float for consistency (again, in case filled above)
            for price_col in ['open', 'high', 'low', 'close']:
                df[price_col] = pd.to_numeric(df[price_col], errors='coerce')

            # If any OHLC field still has NaN, drop those rows—they are not valid bars
            df = df.dropna(subset=['open', 'high', 'low', 'close'])

            # (Optional) Debug: show last 30 cleaned bars in expander
            with st.expander("🧪 Raw 1-Minute Data After Cleaning"):
                st.dataframe(df[['timestamp', 'open', 'high', 'low', 'close']].tail(30))

            max_bars = len(df)
            bars_to_use = st.slider(
                "Last N Bars",
                min_value=20,
                max_value=max_bars,
                value=150  # always default to 150 bars
            )
            if st.button("📥 Load Data", type="primary"):
                st.session_state.df_to_use = df.tail(bars_to_use)
                st.session_state.analysis_results = {}
                st.success(f"Loaded {selected_symbol} {selected_timeframe} [{bars_to_use} bars]")
        except Exception as e:
            st.error(f"⚠️ File `{full_path.name}` is not a valid Parquet file or is corrupted. Please check your files.\n\nError: {e}")
            st.session_state.df_to_use = None

    # --- Auto-Refresh controls ---
    enable_auto_refresh = st.checkbox("Enable Auto-Refresh", value=True)
    refresh_interval = st.number_input("Refresh Interval (seconds)", min_value=10, max_value=600, value=60, step=10)

    if enable_auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, limit=None, key="autorefresh")

    # Analysis settings (only show if data loaded)
    if st.session_state.df_to_use is not None:
        st.divider()
        st.header("⚙️ Analysis Settings")
        st.subheader("Analysis Modules")
        show_smc = st.checkbox("Smart Money Concepts", value=True)
        show_wyckoff = st.checkbox("Wyckoff Analysis", value=True)
        show_volume_profile = st.checkbox("Volume Profile", value=True)
        show_indicators = st.checkbox("Technical Indicators", value=True)
        st.subheader("Visualization Options")
        chart_type = st.selectbox("Chart Type", ["Candlestick", "Heikin Ashi", "Line"])
        show_volume = st.checkbox("Show Volume", value=True)
        show_orderflow = st.checkbox("Show Order Flow", value=True)
        if st.button("🔍 Run Analysis", type="primary"):
            with st.spinner("Running comprehensive analysis..."):
                try:
                    tf_data = st.session_state.df_to_use
                    smc = SMCAnalyzer() if show_smc else None
                    wyckoff = WyckoffAnalyzer() if show_wyckoff else None
                    volume_profile = VolumeProfileAnalyzer() if show_volume_profile else None
                    ta = TechnicalAnalysis() if show_indicators else None
                    results = {}
                    if smc:
                        results['smc'] = smc.analyze(tf_data)
                    if wyckoff:
                        results['wyckoff'] = wyckoff.analyze(tf_data)
                    if volume_profile:
                        results['volume_profile'] = volume_profile.analyze(tf_data)
                    if ta:
                        results['indicators'] = ta.calculate_all(tf_data)
                    st.session_state.analysis_results = results
                    st.success("✅ Analysis complete!")
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")

# Main Content Area
if st.session_state.df_to_use is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Chart", "📈 Market Structure", "📋 Reports", "🧠 QRT Dashboard"])

    with tab1:
        tf_data = st.session_state.df_to_use
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            current_price = tf_data['close'].iloc[-1]
            price_change = ((current_price - tf_data['close'].iloc[-2]) / tf_data['close'].iloc[-2]) * 100
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Current Price", f"${current_price:.5f}", f"{price_change:+.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            volume_col = 'volume' if 'volume' in tf_data.columns else 'tick_volume' if 'tick_volume' in tf_data.columns else None
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            if volume_col:
                st.metric("24h Volume", f"{tf_data[volume_col].tail(24).sum():,.0f}")
            else:
                st.metric("24h Volume", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("Volatility", f"{tf_data['close'].pct_change().std() * 100:.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)
        with col4:
            high_24h = tf_data['high'].tail(24).max()
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("24h High", f"${high_24h:.5f}")
            st.markdown("</div>", unsafe_allow_html=True)
        with col5:
            low_24h = tf_data['low'].tail(24).min()
            st.markdown(
                "<div style='background: #181818; border-radius:7px; padding:8px 4px; margin-bottom:8px'>",
                unsafe_allow_html=True)
            st.metric("24h Low", f"${low_24h:.5f}")
            st.markdown("</div>", unsafe_allow_html=True)

        # --- All chart overlays and hot areas MUST use unified color constants and style (see top of file) ---
        chart_builder = ChartBuilder()
        fig = chart_builder.create_main_chart(
            tf_data,
            "Current",
            chart_type=chart_type,
            show_volume=show_volume,
            analysis_results=st.session_state.analysis_results
        )
        # Apply unified chart style
        fig = apply_dashboard_style(fig, title="Main Chart")
        # NOTE: ChartBuilder/AnalysisPanel overlays must use unified color constants (FVG_BULL_COLOR, etc.) and the same vrect style.
        st.plotly_chart(fig, use_container_width=True)

        if st.session_state.analysis_results:
            analysis_panel = AnalysisPanel()
            analysis_panel.display_results(st.session_state.analysis_results)

    with tab2:
        st.header("Market Structure Analysis")
        # NOTE: Any chart overlays for SMC/Wyckoff zones must use the unified style/colors as per constants above.
        tf_data = st.session_state.df_to_use
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Smart Money Concepts")
            if 'smc' in st.session_state.analysis_results:
                smc_results = st.session_state.analysis_results['smc']
                st.markdown("#### Liquidity Zones")
                for zone in smc_results.get('liquidity_zones', [])[:5]:
                    zone_type = "🔴 Sell-side" if zone['type'] == 'SSL' else "🟢 Buy-side"
                    st.write(f"{zone_type}: ${zone['level']:.5f} (Strength: {zone['strength']:.2f})")
                st.markdown("#### Order Blocks")
                for ob in smc_results.get('order_blocks', [])[:5]:
                    ob_type = "🟢 Bullish" if ob['type'] == 'bullish' else "🔴 Bearish"
                    st.write(f"{ob_type}: ${ob['start']:.5f} - ${ob['end']:.5f}")
        with col2:
            st.subheader("Wyckoff Analysis")
            if 'wyckoff' in st.session_state.analysis_results:
                wyckoff_results = st.session_state.analysis_results['wyckoff']
                st.markdown("#### Current Phase")
                phase = wyckoff_results.get('current_phase', 'Unknown')
                phase_emoji = {
                    'Accumulation': '📈',
                    'Markup': '🚀',
                    'Distribution': '📉',
                    'Markdown': '💥'
                }.get(phase, '❓')
                st.write(f"{phase_emoji} **{phase}**")
                st.markdown("#### Recent Events")
                # PATCH: robust timestamp formatting for Wyckoff events (if present)
                for event in wyckoff_results.get('events', [])[:5]:
                    price = event.get('price')
                    # Try to show event time if present
                    time_str = ""
                    timestamp = event.get('timestamp') or event.get('datetime')
                    if pd.notnull(timestamp) if 'timestamp' in event or 'datetime' in event else False:
                        if not isinstance(timestamp, pd.Timestamp):
                            try:
                                timestamp = pd.to_datetime(timestamp)
                            except Exception:
                                timestamp = None
                        if timestamp is not None and pd.notnull(timestamp):
                            time_str = timestamp.strftime('%Y-%m-%d %H:%M')
                        else:
                            time_str = ""
                    st.write(f"• {event['type']} at ${price:.5f}" + (f" ({time_str})" if time_str else ""))

    with tab3:
        st.header("Analysis Reports")
        tf_data = st.session_state.df_to_use
        if st.button("📄 Generate Full Report"):
            with st.spinner("Generating comprehensive report..."):
                report = f"""
# Zanflow Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Market Overview
- **Current Price**: ${tf_data['close'].iloc[-1]:.5f}
- **24h Change**: {((tf_data['close'].iloc[-1] - tf_data['close'].iloc[-24]) / tf_data['close'].iloc[-24] * 100):.2f}%

## Analysis Summary
"""
                if st.session_state.analysis_results:
                    for module, results in st.session_state.analysis_results.items():
                        report += f"\n### {module.upper()} Analysis\n"
                        report += str(results)[:500] + "...\n"
                st.text_area("Report Preview", report, height=400)
                st.download_button(
                    label="📥 Download Report",
                    data=report,
                    file_name=f"zanflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        with st.expander("🗂 JSON Breakdown Commentary"):
            st.markdown("The following is a human-readable explanation of the core analysis JSON output.")
            if st.session_state.analysis_results:
                for module, results in st.session_state.analysis_results.items():
                    st.subheader(f"{module.upper()} Commentary")
                    # PATCH: robust timestamp formatting for commentary (if events present)
                    if module == "wyckoff" and isinstance(results, dict) and "events" in results:
                        events = results["events"]
                        # Format time for each event if possible
                        formatted_events = []
                        for event in events:
                            event_copy = dict(event)
                            timestamp = event.get('timestamp') or event.get('datetime')
                            if pd.notnull(timestamp) if 'timestamp' in event or 'datetime' in event else False:
                                if not isinstance(timestamp, pd.Timestamp):
                                    try:
                                        timestamp = pd.to_datetime(timestamp)
                                    except Exception:
                                        timestamp = None
                                if timestamp is not None and pd.notnull(timestamp):
                                    event_copy['time_str'] = timestamp.strftime('%Y-%m-%d %H:%M')
                                else:
                                    event_copy['time_str'] = str(timestamp)
                            formatted_events.append(event_copy)
                        display_results = dict(results)
                        display_results["events"] = formatted_events
                        st.json(display_results)
                    else:
                        st.json(results)
            st.download_button(
                label="📥 Download Full JSON",
                data=json.dumps(st.session_state.analysis_results, indent=2, default=str),
                file_name=f"zanflow_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    with tab4:
        qrt_analyzer = QRTQuantumAnalyzer(config_path="./config/qrt_config.yaml")
        qrt_analyzer.create_qrt_dashboard(st.session_state.df_to_use, f"{selected_symbol} {selected_timeframe}")

else:
    st.info("👈 Please select and load a Parquet data file from the sidebar to begin analysis")
    with st.expander("📖 How to Use This Dashboard"):
        st.markdown('''
        1. **Load Data**: Place your Parquet files in the configured data folder and select from the sidebar
        2. **Configure Analysis**: Choose which analysis modules to run and visualization options
        3. **Run Analysis**: Click the "Run Analysis" button to process the data
        4. **Explore Results**: Navigate through the tabs to view different aspects of the analysis
        5. **Export Reports**: Generate and download comprehensive analysis reports

        ### Data Format
        Your Parquet file should have the following columns (case-insensitive, all will be lowercased):
        - Date/Time
        - Open
        - High
        - Low
        - Close
        - Volume

        ### Available Analysis Modules
        - **Smart Money Concepts**: Liquidity zones, order blocks, fair value gaps
        - **Wyckoff Analysis**: Market phases, accumulation/distribution patterns
        - **Volume Profile**: Point of control, value areas, volume nodes
        - **Technical Indicators**: Moving averages, RSI, MACD, Bollinger Bands
''')

