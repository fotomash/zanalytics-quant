"""
Zanalytics Pulse — Position Tracker
A streamlined view of open positions and vitals.
"""
import streamlit as st
import pandas as pd
import os
import requests
import json
import base64
from dotenv import load_dotenv

# Dashboard-local imports
from dashboard.utils.plotly_donuts import bipolar_donut, oneway_donut, behavioral_score_from_mirror
from dashboard.pages.components.market_header import render_market_header

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎯 Zanalytics Pulse — Position Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMAGE BACKGROUND & STYLING ---
@st.cache_data(ttl=3600)
def _get_image_as_base64(path: str):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

_img_base64 = _get_image_as_base64("image_af247b.jpg")
if _img_base64:
    _background_style = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background-image: linear-gradient(rgba(0,0,0,0.80), rgba(0,0,0,0.80)), url(data:image/jpeg;base64,{_img_base64});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .main .block-container {{
        background-color: rgba(0,0,0,0.025) !important;
    }}
    </style>
    """
    st.markdown(_background_style, unsafe_allow_html=True)

# --- API UTILITIES (for vitals) ---
def _pulse_url(path: str) -> str:
    """Normalize paths to pulse endpoints."""
    try:
        base = os.getenv("DJANGO_API_URL", "http://django:8000").rstrip('/')
    except Exception:
        base = "http://django:8000"
    p = path.lstrip('/')
    if p.startswith('api/'):
        return f"{base}/{p}"
    return f"{base}/api/pulse/{p}"

def safe_api_call(method: str, path:str, payload: dict = None, timeout: float = 1.2) -> dict:
    """Safe API call with error handling."""
    try:
        url = _pulse_url(path)
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload or {}, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}", "url": url}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "url": _pulse_url(path)}

# --- HEADER & VITALS ---
render_market_header()

st.subheader("💰 Session Vitals")

try:
    mirror = safe_api_call('GET', 'api/v1/mirror/state') or {}
    acct = safe_api_call('GET', 'api/v1/account/info') or {}
    risk = safe_api_call('GET', 'api/v1/account/risk') or {}

    eq = float(acct.get('equity', 0.0))
    bal = float(acct.get('balance', 0.0))
    sod = float(risk.get('sod_equity', bal or eq))
    target_amt = float(risk.get('target_amount', 0.0))
    loss_amt = float(risk.get('loss_amount', 0.0))
    pnl_today = eq - sod
    exp_pct = risk.get('exposure_pct', 0.0)
    exp_ratio = float(exp_pct / 100.0 if exp_pct and exp_pct > 1 else (exp_pct or 0.0))
    bhv_score = behavioral_score_from_mirror(mirror)
    bhv_ratio = float(bhv_score / 100.0) if bhv_score is not None else 0.0

    cV1, cV2, cV3 = st.columns(3)
    with cV1:
        st.plotly_chart(
            bipolar_donut(
                title="Equity vs SoD",
                value=pnl_today,
                pos_max=max(1.0, target_amt),
                neg_max=max(1.0, loss_amt),
                center_title=f"{{eq:,.0f}}",
                center_sub=f"{{pnl_today:+,.0f}} today",
            ),
            use_container_width=True,
        )
    with cV2:
        st.plotly_chart(
            oneway_donut(
                title="Position Exposure",
                frac=max(0.0, min(1.0, exp_ratio)),
                center_title=f"{{exp_ratio*100:.0f}}%",
                center_sub="of daily risk budget",
            ),
            use_container_width=True,
        )
    with cV3:
        st.plotly_chart(
            oneway_donut(
                title="Behavioral Posture",
                frac=max(0.0, min(1.0, bhv_ratio)),
                center_title=f"{{bhv_score:.0f}}",
                center_sub="composite",
            ),
            use_container_width=True,
        )
except Exception as e:
    st.error(f"Could not load session vitals. Error: {e}")

# --- OPEN POSITIONS ---
st.subheader("📂 Open Positions")

df_trades = pd.DataFrame()

# Fetch positions from MT5
if MT5_AVAILABLE:
    if not mt5.terminal_state().connected:
        login = os.getenv('MT5_LOGIN')
        password = os.getenv('MT5_PASSWORD')
        server = os.getenv('MT5_SERVER')
        if login and password and server:
            if not mt5.initialize(login=int(login), password=password, server=server):
                st.warning("MT5 connection failed. Check credentials.")
        else:
            st.warning("MT5 credentials not found in .env file.")

    if mt5.terminal_state().connected:
        positions = mt5.positions_get()
        if positions:
            df_trades = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
else:
    # Fallback to API if MT5 is not available
    st.info("MT5 library not found. Trying to fetch positions from API...")
    api_positions = safe_api_call('GET', 'api/v1/positions/live')
    if isinstance(api_positions, list) and api_positions:
        df_trades = pd.DataFrame(api_positions)
    elif isinstance(api_positions, dict) and 'error' in api_positions:
        st.error(f"API Error: {api_positions['error']}")


if not df_trades.empty:
    # Standardize column names from different sources
    rename_map = {
        'price_open': 'entry_price',
        'profit': 'pnl',
        'price_current': 'current_price'
    }
    df_trades.rename(columns=rename_map, inplace=True)

    # Map position type from integer to string (for MT5 source)
    if 'type' in df_trades.columns and pd.api.types.is_numeric_dtype(df_trades['type']):
        df_trades['type'] = df_trades['type'].map({0: 'BUY', 1: 'SELL'})

    # Ensure all required columns are present
    required_cols = ['symbol', 'type', 'entry_price', 'current_price', 'pnl']
    if all(col in df_trades.columns for col in required_cols):
        for idx, row in df_trades[required_cols].iterrows():
            cols = st.columns([2, 2, 2, 2, 2, 3])
            cols[0].write(row["symbol"])
            cols[1].write(row["type"])
            cols[2].write(f"{{row['entry_price']:.5f}}")
            cols[3].write(f"{{row['current_price']:.5f}}")
            pnl_color = "#22C55E" if row["pnl"] >= 0 else "#EF4444"
            cols[4].markdown(f"<div style='color:{pnl_color}; font-weight:bold'>{{row['pnl']:+.2f}}</div>", unsafe_allow_html=True)
            
            with cols[5]:
                st.button("SL → BE", key=f"slbe_{idx}")
                st.button("Trail 25%", key=f"trail25_{idx}")
                st.button("Trail 50%", key=f"trail50_{idx}")
                st.button("Partial 25%", key=f"partial25_{idx}")
                st.button("Partial 50%", key=f"partial50_{idx}")
    else:
        st.warning("Positions data is missing required columns for the detailed view.")
        st.dataframe(df_trades)
else:
    st.info("No open positions found.")

