#!/usr/bin/env python3
# Configuration loading order:
# 1. Try to load each config variable from environment variable (os.getenv).
# 2. If not set, fall back to st.secrets (from secrets.toml).
# 3. If not found in either, use a minimal default (None or "./data" for directories).
# All environment variable names are UPPER_SNAKE_CASE (e.g. DATA_DIRECTORY, RAW_DATA_DIRECTORY, FINNHUB_API_KEY, etc.).
# Use get_config_var(name, default) to access config throughout the app.
"""
Zanalytics Dashboard

A focused dashboard providing at-a-glance market intelligence and an overview of available data.
"""
import streamlit as st

# --- PATCH: Load .env config if present ---
from pathlib import Path
from dotenv import load_dotenv
import sys

# Ensure project root is on path for imports
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from utils.enrichment import enrich_ticks
from api_integration.mt5_api_client import Mt5APIClient
import os
load_dotenv(dotenv_path=Path(__file__).parents[2] / '.env')

# --- Config utility: get_config_var ---
def get_config_var(name, default=None):
    v = os.getenv(name)
    if v is not None:
        return v
    try:
        return st.secrets[name.lower()]
    except Exception:
        return default

# Set Streamlit page config as the very first Streamlit command
st.set_page_config(
    page_title="Zanalytics Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
# import os  # Already imported above
import glob
# from pathlib import Path  # Already imported above
from datetime import datetime
import warnings
import re
from typing import Dict, Optional
import base64
import yfinance as yf
from fredapi import Fred
import os
import requests
# --- PATCH: Caching Utilities (robust, writable path) ---
import pickle

def _choose_cache_dir() -> str:
    candidates = []
    for key in ("ZAN_CACHE_DIR", "CACHE_DIR", "STREAMLIT_CACHE_DIR"):
        v = os.getenv(key)
        if v:
            candidates.append(Path(v))
    candidates.append(Path(__file__).resolve().parents[2] / ".cache")
    xdg = os.getenv("XDG_CACHE_HOME")
    if xdg:
        candidates.append(Path(xdg) / "zanalytics-pulse")
    try:
        candidates.append(Path.home() / ".cache" / "zanalytics-pulse")
    except Exception:
        pass
    candidates.append(Path("/tmp") / "zanalytics-cache")
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            # quick write test
            testf = p / ".write_test"
            with open(testf, "w") as f:
                f.write("ok")
            try:
                testf.unlink()
            except Exception:
                pass
            return str(p)
        except Exception:
            continue
    return "/tmp/zanalytics-cache"

_CACHE_DIR = _choose_cache_dir()

def ensure_cache_dir():
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
    except Exception:
        pass

def auto_cache(key, fetch_fn, refresh=False):
    ensure_cache_dir()
    cache_file = os.path.join(_CACHE_DIR, f"{key}.pkl")
    if not refresh and os.path.exists(cache_file):
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    result = fetch_fn()
    with open(cache_file, "wb") as f:
        pickle.dump(result, f)
    return result

def get_cache_timestamp(key: str):
    """Return modification time of cached file if it exists."""
    ensure_cache_dir()
    cache_file = os.path.join(_CACHE_DIR, f"{key}.pkl")
    if os.path.exists(cache_file):
        return datetime.fromtimestamp(os.path.getmtime(cache_file))
    return None

# Suppress warnings for a cleaner output
# Suppress warnings for a cleaner output
warnings.filterwarnings('ignore')


# --- Utility Function for Background Image ---
def get_image_as_base64(path):
    """Reads an image file and returns its base64 encoded string."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Background image not found at '{path}'. Please ensure it's in the same directory as the script.")
        return None


# --- Economic Data Manager ---
class EconomicDataManager:
    """ Manages fetching live economic data using yfinance. """

    def get_dxy_data(self) -> Optional[pd.DataFrame]:
        """ Fetches 15-min OHLC data for DXY for the last 60 days. """
        try:
            ticker = yf.Ticker("DX-Y.NYB")
            hist = ticker.history(period="60d", interval="15m")
            if not hist.empty:
                return hist.tail(100)  # Last 100 M15 bars
            return None
        except Exception:
            return None

class ZanalyticsDashboard:
    # FINNHUB_API_KEY available, not currently used
    # NEWSAPI_KEY available, not currently used
    # TRADING_ECONOMICS_API_KEY available, not currently used
    # OPENAI_API_KEY available, not currently used

    def __init__(self):
        """
        Initializes the dashboard, loading configuration from env or Streamlit secrets.
        """
        # Always use get_config_var for all config values
        self.data_dir = Path(get_config_var("DATA_DIRECTORY", "./data"))
        self.raw_data_dir = Path(get_config_var("RAW_DATA_DIRECTORY", "./data/raw"))
        self.parquet_data_dir = Path(get_config_var("PARQUET_DATA_DIR", "./data/parquet"))
        self.bar_data_dir = Path(get_config_var("BAR_DATA_DIR", "./data/_bars"))
        self.json_dir = Path(get_config_var("JSONDIR", "./data/json"))
        self.data_path = Path(get_config_var("DATA_PATH", "./data"))
        self.supported_pairs = [
            "XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "ETHUSD", "USDCAD",
            "AUDUSD", "NZDUSD", "DXY", "DXYCAS"
        ]
        self.timeframes = ["1min", "5min", "15min", "30min", "1H", "4H", "1D", "1W", "5T"]

        # Base URLs for backend APIs
        self.api_url = get_config_var("MT5_API_URL", "http://localhost:5001")
        self.django_api_url = get_config_var(
            "DJANGO_API_URL", "http://localhost:8000"
        )

        self.economic_manager = EconomicDataManager()
        self.mt5_client = Mt5APIClient(base_url=self.api_url)

        fred_api_key = get_config_var("FRED_API_KEY")
        if not fred_api_key:
            st.error("FRED_API_KEY is missing. Please set it in your environment or Streamlit secrets.")
            raise RuntimeError("FRED_API_KEY is missing. Please set it in your environment or Streamlit secrets.")
        try:
            self.fred = Fred(api_key=fred_api_key)
        except Exception as e:
            st.error(f"Failed to initialize FRED API: {e}")
            raise

        # Example: Add Alpha Vantage/YFinance/MT5 as needed
        # To add more APIs, always use get_config_var("KEY_NAME")

        if 'chart_theme' not in st.session_state:
            st.session_state.chart_theme = 'plotly_dark'

    def fetch_bar_data(self, symbol: str, interval: str = "M15", limit: int = 200) -> pd.DataFrame:
        """Retrieve bar data from the backend API and apply enrichment."""
        df = self.mt5_client.get_bars(symbol, interval, limit)
        return enrich_ticks(df)

    def fetch_tick_data(self, symbol: str, limit: int = 1000) -> pd.DataFrame:
        """Retrieve tick data from the backend API."""
        return self.mt5_client.get_ticks(symbol, limit)

    def run(self):
        # PATCH: Add refresh button and cache file sidebar
        if "refresh_home_data" not in st.session_state:
            st.session_state["refresh_home_data"] = False
        # Move the refresh button to the sidebar
        refresh_home_data = st.sidebar.button("🔄 Refresh Cache", key="refresh_home")
        if refresh_home_data:
            st.session_state["refresh_home_data"] = True
        # Visual cache indicator in sidebar
        cache_file = os.path.join(".cache", "home_data_sources.pkl")
        if os.path.exists(cache_file):
            st.sidebar.success("✅ Cache present")
        else:
            st.sidebar.warning("⚠️ No cache")

        # Enrichment controls
        if "run_enrichment" not in st.session_state:
            st.session_state["run_enrichment"] = False
        run_enrichment_btn = st.sidebar.button("Run Enrichment", key="run_enrichment_btn")
        if run_enrichment_btn:
            st.session_state["run_enrichment"] = True
        ts = get_cache_timestamp("home_chart_xauusd_15min_enriched")
        if ts:
            st.sidebar.write(f"Last enrichment: {ts.strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            background-color: rgba(0,0,0,0.8) !important;
            box-shadow: none !important;
        }
        button[kind="secondary"] {
            background-color: #242424 !important;
            color: #fff !important;
            border: 1px solid rgba(250,250,250,0.12) !important;
            font-weight: 600 !important;
            padding: 0.5em 1em !important;
            border-radius: 8px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        img_base64 = get_image_as_base64("image_af247b.jpg")
        if img_base64:
            background_style = f"""
            <style>
            [data-testid="stAppViewContainer"] > .main {{
                background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url(data:image/jpeg;base64,{img_base64});
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            </style>
            """
            st.markdown(background_style, unsafe_allow_html=True)
        # Patch: Add semi-transparent panel background after image is set
        st.markdown("""
        <style>
        .main .block-container {
            background-color: rgba(0,0,0,0.025) !important;
        }
        </style>
        """, unsafe_allow_html=True)


        if not self.data_dir.exists():
            st.error(f"Data directory not found at: `{self.data_dir}`")
            st.info(
                "Please create this directory or configure the correct path in your `.streamlit/secrets.toml` file.")
            st.code('data_directory = "/path/to/your/data"')
            return

        # --- Tick Data from API ---
        with st.expander("📡 Tick Data – XAUUSD (Last 100 Ticks)", expanded=False):
            try:
                df_ticks = self.fetch_tick_data("XAUUSD", 100)
                if df_ticks.empty:
                    st.warning("No tick data received from API.")
                else:
                    # Show basic columns if available
                    cols = [c for c in ['timestamp', 'bid', 'ask', 'last', 'volume'] if c in df_ticks.columns]
                    st.dataframe(df_ticks[cols])
            except Exception as e:
                st.error(f"Failed to load tick data: {e}")

        with st.spinner("🛰️ Scanning all data sources..."):
            data_sources = auto_cache(
                "home_data_sources",
                lambda: self.scan_all_data_sources(),
                refresh=st.session_state.get("refresh_home_data", False)
            )
        # Moved st.success to display_home_page
        self.display_home_page(data_sources)
        # PATCH: Reset refresh flag at end of run
        if "refresh_home_data" in st.session_state and st.session_state["refresh_home_data"]:
            st.session_state["refresh_home_data"] = False

    def display_home_page(self, data_sources):
        # --- Quant-Desk Welcome Block (Updated Design) ---
        st.markdown(
            """
            <div style='
                margin: 0 auto 1.1rem auto;
                max-width: 100%;
                width: 100%;
                text-align: center;
                padding: 0.2em 0 0.1em 0;
                background: linear-gradient(to right, rgba(103,116,255,0.15), rgba(176,66,255,0.15));
                border-radius: 12px;
                border: 2px solid rgba(251,213,1,0.4);
                box-shadow: 0 2px 12px rgba(103,116,255,0.10);
            '>
                <span style='
                    font-family: "Segoe UI", "Montserrat", "Inter", "Arial", sans-serif;
                    font-size: 2.1rem;
                    font-weight: 800;
                    color: #fff;
                    letter-spacing: 0.02em;
                    display: block;
                    margin-bottom: 0.13em;
                    text-transform: uppercase;
                '>
                    ZANALYTICS
                </span>
                <span style='
                    font-family: "Segoe UI", "Montserrat", "Inter", "Arial", sans-serif;
                    font-size: 1.12rem;
                    color: #eee;
                    font-weight: 600;
                    display: block;
                    margin-bottom: 0.19em;
                '>
                    AI / ML Powered Global Market Intelligence
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- Microstructure 3D Surface Demo (XAUUSD) ---
        import plotly.graph_objects as go

        df_ticks = self.fetch_tick_data("XAUUSD", 1000)
        if not df_ticks.empty:
            try:
                if 'bid' in df_ticks.columns and 'ask' in df_ticks.columns:
                    df_ticks['price_mid'] = (df_ticks['bid'] + df_ticks['ask']) / 2
                else:
                    df_ticks['price_mid'] = df_ticks.get('last')
                df_ticks['inferred_volume'] = df_ticks.get('volume', 1)

                # Bin timestamps and price for 3D surface
                time_bins = pd.cut(df_ticks.index, bins=50, labels=False)
                price_bins = pd.cut(df_ticks['price_mid'], bins=50, labels=False)
                surface_data = pd.pivot_table(
                    df_ticks, values='inferred_volume',
                    index=price_bins, columns=time_bins,
                    aggfunc='sum', fill_value=0
                )

                if not surface_data.empty:
                    fig = go.Figure(
                        data=[go.Surface(
                            z=surface_data.values,
                            colorscale='Viridis',
                            name='Volume Surface'
                        )]
                    )
                    fig.update_layout(
                        title="XAUUSD Microstructure 3D Volume Map (Recent Tick Data)",
                        autosize=True,
                        height=400,
                        margin=dict(l=40, r=40, t=60, b=40),
                        template=st.session_state.get('chart_theme', 'plotly_dark'),
                        scene=dict(
                            xaxis_title="Time Bin",
                            yaxis_title="Price Bin",
                            zaxis_title="Inferred Volume"
                        ),
                        paper_bgcolor="rgba(0,0,0,0.02)",
                        plot_bgcolor="rgba(0,0,0,0.02)",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough tick data for 3D surface.")
            except Exception as e:
                st.warning(f"Error processing tick data: {e}")
        else:
            st.info("No tick data available for 3D surface demo.")

        # --- XAUUSD 15-Minute Candlestick Chart from Parquet (with FVG, Midas VWAP, Wyckoff Accumulation) ---
        try:
            df = auto_cache(
                "home_chart_xauusd_15min",
                lambda: self.fetch_bar_data("XAUUSD", "M15", 200).sort_values("timestamp"),
                refresh=st.session_state.get("refresh_home_data", False)
            )
            df_enriched = auto_cache(
                "home_chart_xauusd_15min_enriched",
                lambda: enrich_ticks(df),
                refresh=st.session_state.get("run_enrichment", False)
            )
            if st.session_state.get("run_enrichment"):
                st.session_state["run_enrichment"] = False
            # === PATCH: Only show latest data, not file path ===
            latest_ts = df["timestamp"].max() if "timestamp" in df.columns else "N/A"
            st.info(f"Latest XAUUSD data: {latest_ts}")
            # (Your existing processing/plotting here)
            if "timestamp" not in df.columns:
                st.error("Could not locate a 'timestamp' column in the data.")
            else:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values(by="timestamp")
                    df_recent = df.tail(200)

                    fig_xau = go.Figure(data=[go.Candlestick(
                        x=df_recent["timestamp"],
                        open=df_recent["open"],
                        high=df_recent["high"],
                        low=df_recent["low"],
                        close=df_recent["close"],
                        increasing_line_color='lime',
                        decreasing_line_color='red',
                        name='XAUUSD 15min'
                    )])

                    # --- FVG zone overlays ---
                    for i in range(2, len(df_recent)):
                        prev = df_recent.iloc[i-2]
                        curr = df_recent.iloc[i]
                        # Bullish FVG: current low > previous high
                        if curr["low"] > prev["high"]:
                            fig_xau.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(0,255,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )
                        # Bearish FVG: current high < previous low
                        elif curr["high"] < prev["low"]:
                            fig_xau.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(255,0,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )

                    # --- Anchored VWAP (Midas style, from left edge) ---
                    vwap_prices = (df_recent['high'] + df_recent['low'] + df_recent['close']) / 3
                    cumulative_vol = df_recent['volume'].cumsum()
                    vwap = (vwap_prices * df_recent['volume']).cumsum() / cumulative_vol
                    fig_xau.add_trace(go.Scatter(x=df_recent["timestamp"], y=vwap, mode='lines', name='Midas VWAP',
                                                 line=dict(color='gold', width=2, dash='dot')))

                    import numpy as np

                    # --- Enhanced Wyckoff regime detection and annotation ---
                    phases = []
                    window = 42
                    close = df_recent['close'].values

                    for i in range(len(close) - window):
                        win = close[i:i+window]
                        atr = (df_recent['high'].iloc[i:i+window] - df_recent['low'].iloc[i:i+window]).mean()
                        minmax_range = win.max() - win.min()
                        slope = (win[-1] - win[0]) / window

                        if minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr:
                            phases.append(('accumulation', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope > 0.10 * atr:
                            phases.append(('markup', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr and i > 0:
                            phases.append(('distribution', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope < -0.10 * atr:
                            phases.append(('markdown', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))

                    # Add colored overlays and annotation text
                    phase_colors = {
                        'accumulation': 'rgba(0, 90, 255, 0.08)',
                        'markup': 'rgba(0, 200, 70, 0.08)',
                        'distribution': 'rgba(255, 160, 0, 0.08)',
                        'markdown': 'rgba(220, 40, 40, 0.08)'
                    }

                    # Draw shaded vrects for phases, and annotate once per phase (inside each band)
                    last_phase = None
                    for phase, start, end in phases:
                        fig_xau.add_vrect(
                            x0=start, x1=end,
                            fillcolor=phase_colors[phase], opacity=0.13, line_width=0, layer="below"
                        )
                        # Annotate inside the band for the first occurrence of each phase
                        if phase != last_phase:
                            win = df_recent[(df_recent["timestamp"] >= start) & (df_recent["timestamp"] <= end)]
                            if not win.empty:
                                y_mid = (win['high'].max() + win['low'].min()) / 2
                            else:
                                y_mid = df_recent['close'].iloc[-1]
                            fig_xau.add_annotation(
                                x=start,
                                y=y_mid,
                                text=phase.title(),
                                showarrow=False,
                                font=dict(size=13, color=phase_colors[phase].replace("0.08", "0.8")),
                                bgcolor="rgba(0,0,0,0.4)",
                                yshift=0,
                                opacity=0.9
                            )
                            last_phase = phase

                    # --- Add phase annotation to the chart title ---
                    current_phase = None
                    if phases:
                        # Pick regime whose end is latest (or overlaps last timestamp)
                        last_ts = df_recent["timestamp"].max()
                        for phase, start, end in reversed(phases):
                            if end >= last_ts:
                                current_phase = phase
                                break
                        if not current_phase:
                            # fallback: just use the last detected
                            current_phase = phases[-1][0]

                    phase_label = f"Wyckoff: <b style='color:orange;'>{current_phase.upper()}</b>" if current_phase else ""
                    chart_title = f"XAUUSD – 15-Minute Candlestick Chart with FVG, Midas VWAP & {phase_label}"

                    fig_xau.update_layout(
                        title={
                            'text': chart_title,
                            'y':0.93,
                            'x':0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'
                        },
                        template=st.session_state.get('chart_theme', 'plotly_dark'),
                        height=460,
                        autosize=True,
                        paper_bgcolor="rgba(0,0,0,0.02)",
                        plot_bgcolor="rgba(0,0,0,0.02)",
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    # Remove the legend from the top-right
                    fig_xau.update_layout(showlegend=False)
                    # Plot the chart directly at top-level so it stretches full width
                    st.plotly_chart(fig_xau, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load XAUUSD 15min candlestick chart: {e}")

        # --- EURUSD and GBPUSD 15-Minute Candlestick Charts (with FVG, Midas VWAP, Wyckoff) ---
        """
        for fx_pair in ["EURUSD", "GBPUSD"]:
            try:
                df = auto_cache(
                    f"home_chart_{fx_pair.lower()}_15min",
                    lambda p=fx_pair: self.fetch_bar_data(p, "M15", 200).sort_values("timestamp"),
                    refresh=st.session_state.get("refresh_home_data", False)
                )
                required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
                if not required_cols.issubset(df.columns):
                    st.info(f"{fx_pair} 15min data missing required columns: {required_cols - set(df.columns)}")
                    continue
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values(by="timestamp")
                    df_recent = df.tail(200)

                    fig_fx = go.Figure(data=[go.Candlestick(
                        x=df_recent["timestamp"],
                        open=df_recent["open"],
                        high=df_recent["high"],
                        low=df_recent["low"],
                        close=df_recent["close"],
                        increasing_line_color='lime',
                        decreasing_line_color='red',
                        name=f'{fx_pair} 15min'
                    )])

                    # FVG overlays
                    for i in range(2, len(df_recent)):
                        prev = df_recent.iloc[i-2]
                        curr = df_recent.iloc[i]
                        if curr["low"] > prev["high"]:
                            fig_fx.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(0,255,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )
                        elif curr["high"] < prev["low"]:
                            fig_fx.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(255,0,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )

                    # Anchored VWAP (Midas style)
                    vwap_prices = (df_recent['high'] + df_recent['low'] + df_recent['close']) / 3
                    cumulative_vol = df_recent['volume'].cumsum()
                    vwap = (vwap_prices * df_recent['volume']).cumsum() / cumulative_vol
                    fig_fx.add_trace(go.Scatter(x=df_recent["timestamp"], y=vwap, mode='lines', name='Midas VWAP',
                                                line=dict(color='gold', width=2, dash='dot')))

                    # Wyckoff regime detection
                    phases = []
                    window = 42
                    close = df_recent['close'].values
                    for i in range(len(close) - window):
                        win = close[i:i+window]
                        atr = (df_recent['high'].iloc[i:i+window] - df_recent['low'].iloc[i:i+window]).mean()
                        minmax_range = win.max() - win.min()
                        slope = (win[-1] - win[0]) / window
                        if minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr:
                            phases.append(('accumulation', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope > 0.10 * atr:
                            phases.append(('markup', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr and i > 0:
                            phases.append(('distribution', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope < -0.10 * atr:
                            phases.append(('markdown', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                    phase_colors = {
                        'accumulation': 'rgba(0, 90, 255, 0.08)',
                        'markup': 'rgba(0, 200, 70, 0.08)',
                        'distribution': 'rgba(255, 160, 0, 0.08)',
                        'markdown': 'rgba(220, 40, 40, 0.08)'
                    }
                    last_phase = None
                    for phase, start, end in phases:
                        fig_fx.add_vrect(
                            x0=start, x1=end,
                            fillcolor=phase_colors[phase], opacity=0.13, line_width=0, layer="below"
                        )
                        if phase != last_phase:
                            win = df_recent[(df_recent["timestamp"] >= start) & (df_recent["timestamp"] <= end)]
                            if not win.empty:
                                y_mid = (win['high'].max() + win['low'].min()) / 2
                            else:
                                y_mid = df_recent['close'].iloc[-1]
                            fig_fx.add_annotation(
                                x=start,
                                y=y_mid,
                                text=phase.title(),
                                showarrow=False,
                                font=dict(size=13, color=phase_colors[phase].replace("0.08", "0.8")),
                                bgcolor="rgba(0,0,0,0.4)",
                                yshift=0,
                                opacity=0.9
                            )
                            last_phase = phase
                    # Chart title with phase
                    current_phase = None
                    if phases:
                        last_ts = df_recent["timestamp"].max()
                        for phase, start, end in reversed(phases):
                            if end >= last_ts:
                                current_phase = phase
                                break
                        if not current_phase:
                            current_phase = phases[-1][0]
                    phase_label = f"Wyckoff: <b style='color:orange;'>{current_phase.upper()}</b>" if current_phase else ""
                    chart_title = f"{fx_pair} – 15-Minute Candlestick Chart with FVG, Midas VWAP & {phase_label}"
                    fig_fx.update_layout(
                        title={
                            'text': chart_title,
                            'y':0.93,
                            'x':0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'
                        },
                        template=st.session_state.get('chart_theme', 'plotly_dark'),
                        height=370,
                        autosize=True,
                        paper_bgcolor="rgba(0,0,0,0.02)",
                        plot_bgcolor="rgba(0,0,0,0.02)",
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=20, r=20, t=40, b=20),
                        showlegend=False
                    )
                    fig_fx.update_layout(showlegend=False)
                    st.plotly_chart(fig_fx, use_container_width=True)
            except Exception as e:
                st.warning(f"Failed to load {fx_pair} 15min candlestick chart: {e}")
        """

        # Insert EURGBP 15-min chart block after GBPUSD
        """
        try:
            fx_pair = "EURGBP"
            df = auto_cache(
                "home_chart_eurgbp_15min",
                lambda: self.fetch_bar_data(fx_pair, "M15", 200).sort_values("timestamp"),
                refresh=st.session_state.get("refresh_home_data", False)
            )
            required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required_cols.issubset(df.columns):
                st.info(f"{fx_pair} 15min data missing required columns: {required_cols - set(df.columns)}")
            else:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp")
                # Confirm that only the last 200 rows are used for plotting
                df_recent = df.tail(200)

                    fig_fx = go.Figure(data=[go.Candlestick(
                        x=df_recent["timestamp"],
                        open=df_recent["open"],
                        high=df_recent["high"],
                        low=df_recent["low"],
                        close=df_recent["close"],
                        increasing_line_color='lime',
                        decreasing_line_color='red',
                        name=f'{fx_pair} 15min'
                    )])

                    # FVG overlays
                    for i in range(2, len(df_recent)):
                        prev = df_recent.iloc[i-2]
                        curr = df_recent.iloc[i]
                        if curr["low"] > prev["high"]:
                            fig_fx.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(0,255,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )
                        elif curr["high"] < prev["low"]:
                            fig_fx.add_vrect(
                                x0=df_recent.iloc[i-1]["timestamp"], x1=curr["timestamp"],
                                fillcolor="rgba(255,0,0,0.13)", opacity=0.26, line_width=0, layer="below"
                            )

                    # Anchored VWAP (Midas style)
                    vwap_prices = (df_recent['high'] + df_recent['low'] + df_recent['close']) / 3
                    cumulative_vol = df_recent['volume'].cumsum()
                    vwap = (vwap_prices * df_recent['volume']).cumsum() / cumulative_vol
                    fig_fx.add_trace(go.Scatter(x=df_recent["timestamp"], y=vwap, mode='lines', name='Midas VWAP',
                                                line=dict(color='gold', width=2, dash='dot')))

                    # Wyckoff regime detection
                    phases = []
                    window = 42
                    close = df_recent['close'].values
                    for i in range(len(close) - window):
                        win = close[i:i+window]
                        atr = (df_recent['high'].iloc[i:i+window] - df_recent['low'].iloc[i:i+window]).mean()
                        minmax_range = win.max() - win.min()
                        slope = (win[-1] - win[0]) / window
                        if minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr:
                            phases.append(('accumulation', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope > 0.10 * atr:
                            phases.append(('markup', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif minmax_range < 1.2 * atr and abs(slope) < 0.08 * atr and i > 0:
                            phases.append(('distribution', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                        elif slope < -0.10 * atr:
                            phases.append(('markdown', df_recent.iloc[i]["timestamp"], df_recent.iloc[i+window]["timestamp"]))
                    phase_colors = {
                        'accumulation': 'rgba(0, 90, 255, 0.08)',
                        'markup': 'rgba(0, 200, 70, 0.08)',
                        'distribution': 'rgba(255, 160, 0, 0.08)',
                        'markdown': 'rgba(220, 40, 40, 0.08)'
                    }
                    last_phase = None
                    for phase, start, end in phases:
                        fig_fx.add_vrect(
                            x0=start, x1=end,
                            fillcolor=phase_colors[phase], opacity=0.13, line_width=0, layer="below"
                        )
                        if phase != last_phase:
                            win = df_recent[(df_recent["timestamp"] >= start) & (df_recent["timestamp"] <= end)]
                            if not win.empty:
                                y_mid = (win['high'].max() + win['low'].min()) / 2
                            else:
                                y_mid = df_recent['close'].iloc[-1]
                            fig_fx.add_annotation(
                                x=start,
                                y=y_mid,
                                text=phase.title(),
                                showarrow=False,
                                font=dict(size=13, color=phase_colors[phase].replace("0.08", "0.8")),
                                bgcolor="rgba(0,0,0,0.4)",
                                yshift=0,
                                opacity=0.9
                            )
                            last_phase = phase
                    # Chart title with phase
                    current_phase = None
                    if phases:
                        last_ts = df_recent["timestamp"].max()
                        for phase, start, end in reversed(phases):
                            if end >= last_ts:
                                current_phase = phase
                                break
                        if not current_phase:
                            current_phase = phases[-1][0]
                    phase_label = f"Wyckoff: <b style='color:orange;'>{current_phase.upper()}</b>" if current_phase else ""
                    chart_title = f"{fx_pair} – 15-Minute Candlestick Chart with FVG, Midas VWAP & {phase_label}"
                    fig_fx.update_layout(
                        title={
                            'text': chart_title,
                            'y':0.93,
                            'x':0.5,
                            'xanchor': 'center',
                            'yanchor': 'top'
                        },
                        template=st.session_state.get('chart_theme', 'plotly_dark'),
                        height=370,
                        autosize=True,
                        paper_bgcolor="rgba(0,0,0,0.02)",
                        plot_bgcolor="rgba(0,0,0,0.02)",
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=20, r=20, t=40, b=20),
                        showlegend=False
                    )
                    fig_fx.update_layout(showlegend=False)
                    st.plotly_chart(fig_fx, use_container_width=True)
        except Exception as e:
            st.warning(f"Failed to load EURGBP 15min candlestick chart: {e}")
        """

        # --- DXY (Broad Dollar Index) Chart using FRED API ---
        try:
            dxy_data = self.fred.get_series('DTWEXBGS')  # Broad Dollar Index
            dxy_data = dxy_data.dropna()
            fig_dxy = go.Figure()
            fig_dxy.add_trace(go.Scatter(x=dxy_data.index, y=dxy_data.values, mode='lines', name='DXY'))
            fig_dxy.update_layout(title='DXY (Broad Dollar Index)', template='plotly_dark')
            st.plotly_chart(fig_dxy, use_container_width=True)
            # --- PATCH: Show original DXY green bar chart after FRED DXY line chart ---
            self.display_original_dxy_chart()
        except Exception as e:
            st.error(f"Failed to load DXY chart: {e}")

        # --- XAUUSD 3D Visualization of FVG & SMC (15min) ---
        try:
            df_3d = self.fetch_bar_data("XAUUSD", "M15", 200)
            if {"timestamp", "close"}.issubset(df_3d.columns):
                df_3d = df_3d.sort_values("timestamp")
                df_3d_recent = df_3d.tail(200)
                x_vals = df_3d_recent["timestamp"]
                y_vals = df_3d_recent["close"]
                z_vals = np.abs(df_3d_recent["close"].diff().fillna(0))
                fig_xau_3d = go.Figure(data=[go.Scatter3d(
                    x=x_vals,
                    y=y_vals,
                    z=z_vals,
                    mode='markers',
                    marker=dict(
                        size=6,
                        color=z_vals,
                        colorscale='Plasma',
                        opacity=0.85,
                        colorbar=dict(title="Volatility"),
                    ),
                    name="FVG & SMC",
                )])
                fig_xau_3d.update_layout(
                    title="XAUUSD - 3D Visualization of FVG & SMC (15min)",
                    scene=dict(
                        xaxis_title="Timestamp",
                        yaxis_title="Close Price",
                        zaxis_title="Volatility (|ΔClose|)"
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    template=st.session_state.get('chart_theme', 'plotly_dark'),
                    height=440,
                    paper_bgcolor="rgba(0,0,0,0.02)",
                    plot_bgcolor="rgba(0,0,0,0.02)",
                )
                st.plotly_chart(fig_xau_3d, use_container_width=True)
                # Render consolidated multi-asset 3-D view
                self.create_multi_asset_3d_chart(data_sources)
            else:
                st.info("XAUUSD 15min data missing 'timestamp' or 'close' column for 3D FVG/SMC chart.")
        except Exception as e:
            st.warning(f"Error loading 3D XAUUSD FVG/SMC chart: {e}")

    # --- Multi-Asset 3D Volume Surface Chart ---
    def create_multi_asset_3d_chart(self, data_sources):
        st.markdown("#### 🌐 Multi-Asset 3D Volume Surface – 15-Minute")

        import numpy as np

        assets = {
            "DXY": "Plasma",
            "EURUSD": "Cividis",
            "GBPUSD": "Viridis",
        }

        surfaces = []

        for idx, (asset, colorscale) in enumerate(assets.items()):
            df = self.fetch_bar_data(asset, "M15", 1000)
            if not {"timestamp", "close", "volume"}.issubset(df.columns):
                continue

            df = df.sort_values("timestamp").tail(1000).copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.dropna(subset=["timestamp", "close", "volume"], inplace=True)

            df["time_bin"] = pd.cut(df.index, bins=50, labels=False)
            df["price_bin"] = pd.cut(df["close"], bins=50, labels=False)

            pivot = pd.pivot_table(
                df,
                values="volume",
                index="price_bin",
                columns="time_bin",
                aggfunc="sum",
                fill_value=0,
            )

            if pivot.empty:
                continue

            surfaces.append(go.Surface(
                z=np.log1p(pivot.values + 1e-3) + idx * 0.4,
                colorscale=colorscale,
                showscale=False,
                name=asset,
                opacity=0.9
            ))

        if surfaces:
            fig = go.Figure(data=surfaces)
            # Add labels at the top center of each surface
            for idx, asset in enumerate(["DXY", "EURUSD", "GBPUSD"]):
                fig.add_trace(go.Scatter3d(
                    x=[25],  # Midpoint of time bins
                    y=[25],  # Midpoint of price bins
                    z=[np.max([surface.z.max() for surface in surfaces]) + idx * 0.4 + 0.1],
                    mode='text',
                    text=[asset],
                    textposition='top center',
                    textfont=dict(size=14, color='white'),
                    showlegend=False
                ))
            fig.update_layout(
                title="Multi-Asset 3D Volume Surface (15-Minute)",
                scene=dict(
                    xaxis_title="Time Bin",
                    yaxis_title="Price Bin",
                    zaxis_title="Volume"
                ),
                template=st.session_state.get("chart_theme", "plotly_dark"),
                height=500,
                paper_bgcolor="rgba(0,0,0,0.02)",
                plot_bgcolor="rgba(0,0,0,0.02)",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=0.02,
                    xanchor="center",
                    x=0.5
                )
            )
            # --- Insert manual legend traces for DXY, EURUSD, GBPUSD ---
            fig.add_trace(go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],
                mode='markers',
                marker=dict(size=8, color='magenta'),
                name='DXY'
            ))
            fig.add_trace(go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],
                mode='markers',
                marker=dict(size=8, color='goldenrod'),
                name='EURUSD'
            ))
            fig.add_trace(go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],
                mode='markers',
                marker=dict(size=8, color='limegreen'),
                name='GBPUSD'
            ))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No suitable data found for volume surface chart.")

        st.markdown("<hr style='margin-top:1.5rem'>", unsafe_allow_html=True)

        latest_yields, previous_yields = self.get_10y_yields()
        st.markdown("""
<style>
.yields-table {
    background: rgba(26,34,45,0.85);
    color: #e7eaf0;
    font-size: 1.05rem;
    border-radius: 8px;
    border: 1px solid rgba(37,48,71,0.4);
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 1.5rem;
    margin-top: 0.5rem;
    width: 100%;
    max-width: 370px;
}
.yields-table th, .yields-table td {
    text-align: center !important;
    padding: 0.25rem 0.6rem;
}
</style>
""", unsafe_allow_html=True)

        st.markdown("<h5 style='text-align:center;'>🌍 10‑Year Government Bond Yields</h5>", unsafe_allow_html=True)
        st.markdown("""
<div style='
    background-color: rgba(0, 0, 0, 0.25);
    padding: 1.1rem;
    margin: 0.8rem 0 1.4rem 0;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
'>
""", unsafe_allow_html=True)
        cols = st.columns(len(latest_yields))
        # --- For sparkline charts ---
        yield_tickers = {
            "US": "DGS10",
            "Germany": "IRLTLT01DEM156N",
            "Japan": "IRLTLT01JPM156N",
            "UK": "IRLTLT01GBM156N",
        }
        for i, (country, val) in enumerate(latest_yields.items()):
            prev_val = previous_yields.get(country)
            delta = None
            if prev_val is not None and val != "N/A":
                delta = round(val - prev_val, 3)
            cols[i].metric(country, f"{val}%" if val != 'N/A' else val, delta)

            # --- Insert mini-chart (sparkline) below metric for each country ---
            try:
                ticker = yield_tickers.get(country)
                if ticker is not None:
                    # Fetch last 50 yield values from FRED
                    series = self.fred.get_series(ticker).dropna()
                    if len(series) >= 2:
                        yvals = series.iloc[-50:].values
                        xvals = list(range(len(yvals)))
                        # Make sparkline plot
                        fig_spark = go.Figure()
                        fig_spark.add_trace(go.Scatter(
                            x=xvals,
                            y=yvals,
                            mode="lines",
                            line=dict(color="#FFD600", width=2),
                            showlegend=False,
                            hoverinfo="skip",
                        ))
                        fig_spark.update_layout(
                            margin=dict(l=0, r=0, t=10, b=10),
                            height=80,
                            width=160,
                            paper_bgcolor="rgba(0,0,0,0.0)",
                            plot_bgcolor="rgba(0,0,0,0.0)",
                        )
                        fig_spark.update_xaxes(visible=False, showgrid=False, zeroline=False)
                        fig_spark.update_yaxes(visible=False, showgrid=False, zeroline=False)
                        cols[i].plotly_chart(fig_spark, use_container_width=False)
            except Exception:
                pass
        st.markdown("</div>", unsafe_allow_html=True)

        # Move the "About Zanalytics Trading Frameworks" expander here, after yields table, before datasets and footer
        with st.expander("ℹ️ About Zanalytics Trading Frameworks"):
            st.markdown("""
            **Wyckoff Methodology:**  
            - Analyzes price and volume to identify the four classic market phases: Accumulation, Markup, Distribution, and Markdown.
            - Tracks composite operator (CO) behavior, supply/demand dynamics, and timing of breakouts using patterns like springs and upthrusts.

            **Smart Money Concepts (SMC):**  
            - Focuses on institutional order flow, mapping liquidity pools, inducements, and engineered stop hunts.
            - Highlights “order blocks” where banks and funds accumulate/distribute positions.

            **Microstructure & Volume Analytics:**  
            - Provides tick-level delta, spread, and footprint charts.
            - Reveals hidden buying/selling pressure and identifies value areas and volume imbalances.

            This dashboard is designed for professionals who demand a statistical, repeatable approach to discretionary or systematic trading.
            """)

        # Insert Zanalytics expander (details) immediately after About Zanalytics Trading Frameworks
        with st.expander("ℹ️ What is Zanalytics? (Click to expand details)"):
            st.markdown("""
            <div style='font-size:1.02rem; color:#e7eaf0;'>
            <b>Institutional-Grade Analytics for Traders & Portfolio Managers</b>
            <br><br>
            This dashboard integrates advanced trading frameworks including
            <b>Wyckoff Methodology</b>, <b>Smart Money Concepts (SMC)</b>, and <b>volume microstructure analysis</b>.
            <br><br>
            Developed for serious traders, it enables deep market phase identification, liquidity zone mapping, and order flow insights,
            supporting decision-making at both tactical and strategic levels.
            <br><br>
            <b>Core Features:</b><br>
            • <b>Wyckoff Analysis:</b> Detect accumulation, distribution, springs, upthrusts, and phase transitions.<br>
            • <b>Smart Money Concepts:</b> Map institutional liquidity pools, order blocks, inducements, and market structure shifts.<br>
            • <b>Microstructure Tools:</b> Tick-level volume, delta, spread, and execution flow visualization.<br>
            • <b>Technical Confluence:</b> Multi-timeframe screening and cross-asset overlays.
            </div>
            """, unsafe_allow_html=True)

        # Horizontal rule before available datasets
        st.markdown("---")
        # ─── Available datasets (bottom, plain) ────────────────────────────────
        self.display_available_data(data_sources)

        st.markdown(
            "<div style='text-align:center; color:#8899a6; font-size:0.97rem; margin-top:2.5rem;'>"
            "© 2025 Zanalytics. Powered by institutional-grade market microstructure analytics.<br>"
            "<span style='font-size:0.92rem;'>Data and visualizations for professional and educational use only.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.success(f"📂  Loaded **{len(data_sources)}** asset folders • **{sum(len(v) for v in data_sources.values())}** timeframe files detected")

    def get_10y_yields(self):
        """Fetches the latest and previous available 10Y government bond yields from FRED."""
        tickers = {
            "US": "DGS10",
            "Germany": "IRLTLT01DEM156N",
            "Japan": "IRLTLT01JPM156N",
            "UK": "IRLTLT01GBM156N",
        }
        latest_yields, previous_yields = {}, {}
        for country, code in tickers.items():
            # PATCH: cache each FRED yield series
            series = auto_cache(
                f"home_{country}_10y_yield_series",
                lambda c=code: self.fred.get_series(c).dropna(),
                refresh=st.session_state.get("refresh_home_data", False)
            )
            try:
                latest = float(series.iloc[-1])
                prev = float(series.iloc[-2]) if len(series) > 1 else None
                latest_yields[country] = round(latest, 3)
                previous_yields[country] = round(prev, 3) if prev else None
            except Exception:
                latest_yields[country] = "N/A"
                previous_yields[country] = None
        return latest_yields, previous_yields

    def display_available_data(self, data_sources):
        """Lists the pairs and timeframes found in the data directory."""
        st.markdown("##### Available Datasets")
        if not data_sources:
            st.warning("No data found in the configured directory.")
            return

        for pair, tfs in sorted(data_sources.items()):
            if tfs:
                # Sort timeframes logically
                tf_list = ", ".join(
                    sorted(tfs.keys(), key=lambda t: (self.timeframes.index(t) if t in self.timeframes else 99, t)))
                st.markdown(f"{pair}: {tf_list}")

    def display_original_dxy_chart(self):
        """
        Render the original DXY green bar chart at the bottom of the page.
        Data is loaded via the API and cached for efficiency.
        """
        import plotly.graph_objects as go
        try:
            df = auto_cache(
                "home_chart_dxy_w1",
                lambda: self.fetch_bar_data("DXY", "W1", 104).sort_values("timestamp"),
                refresh=st.session_state.get("refresh_home_data", False)
            )
            if {"timestamp", "close"}.issubset(df.columns):
                df_recent = df.tail(104)
                st.subheader("DXY – US Dollar Index (Weekly, Last 2 Years)")
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_recent["timestamp"],
                    y=df_recent["close"],
                    marker_color="limegreen",
                    name="DXY (Weekly Close)",
                    opacity=0.92
                ))
                fig.update_layout(
                    template=st.session_state.get('chart_theme', 'plotly_dark'),
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0.02)",
                    plot_bgcolor="rgba(0,0,0,0.02)",
                    margin=dict(l=20, r=20, t=40, b=20),
                    xaxis_title="Week",
                    yaxis_title="DXY Close",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("DXY weekly data missing required columns for chart.")
        except Exception as e:
            st.info(f"Could not load DXY weekly data: {e}")

    def scan_all_data_sources(self):
        """Scans for data files in the configured directory and its subdirectories."""
        data_sources = {}
        # Search for files in the root data directory and any subdirectories
        all_files = glob.glob(os.path.join(self.data_dir, "**", "*.*"), recursive=True)

        for f_path in all_files:
            # Use the parent directory name as the pair if it's a supported pair
            parent_dir_name = Path(f_path).parent.name

            found_pair = None
            if parent_dir_name.upper() in self.supported_pairs:
                found_pair = parent_dir_name.upper()
            else:
                # Fallback to searching the filename
                for pair in self.supported_pairs:
                    if pair in Path(f_path).name:
                        found_pair = pair
                        break

            if found_pair and f_path.endswith(('.csv', '.parquet')):
                for tf in self.timeframes:
                    if tf in Path(f_path).name:
                        if found_pair not in data_sources:
                            data_sources[found_pair] = {}
                        data_sources[found_pair][tf] = f_path
                        break
        return data_sources


if __name__ == "__main__":
    dashboard = ZanalyticsDashboard()
    dashboard.run()
