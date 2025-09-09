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

# --- POSITIONS FETCH HELPER (MT5 → API fallback) ---
# --- POSITIONS FETCH HELPER (MT5 → API fallback, multi-endpoint, multi-shape) ---
def _fetch_positions_df() -> pd.DataFrame:
    """Fetch live positions from MT5 if available; otherwise via Pulse API.
    Tries several endpoints and payload shapes, returns a normalized DataFrame.
    Also records the source endpoint for debugging in st.session_state['positions_source'].
    """
    df = pd.DataFrame()
    st.session_state['positions_source'] = '—'

    # 1) Try MT5 first (if available)
    if MT5_AVAILABLE:
        try:
            if not mt5.terminal_state().connected:
                login = os.getenv('MT5_LOGIN')
                password = os.getenv('MT5_PASSWORD')
                server = os.getenv('MT5_SERVER')
                if login and password and server:
                    try:
                        mt5.initialize(login=int(login), password=password, server=server)
                    except Exception:
                        pass
            if mt5.terminal_state().connected:
                positions = mt5.positions_get()
                if positions:
                    df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
                    st.session_state['positions_source'] = 'MT5'
        except Exception:
            df = pd.DataFrame()

    # 2) Fallback to HTTP API (try multiple Pulse flavors)
    if df.empty:
        endpoints = [
            # Auto-prefixed by _pulse_url to /api/pulse/
            'positions/live',
            'positions/open',
            'positions',
            # Explicit API v1 paths (bypass /api/pulse prefixing)
            'api/v1/positions/live',
            'api/v1/positions/open',
            'api/v1/positions',
        ]

        api_payload = None
        hit_ep = None
        for ep in endpoints:
            res = safe_api_call('GET', ep)
            if isinstance(res, dict) and 'error' in res:
                continue
            api_payload = res
            hit_ep = ep
            break

        # Parse payload into list-of-dicts
        rows = []
        if isinstance(api_payload, list):
            rows = api_payload
        elif isinstance(api_payload, dict):
            for key in ('positions', 'open_positions', 'data', 'results', 'items'):
                val = api_payload.get(key)
                if isinstance(val, list) and val:
                    rows = val
                    break
        # Build DataFrame
        if rows:
            try:
                df = pd.DataFrame(rows)
                st.session_state['positions_source'] = f"API:{hit_ep}"
            except Exception:
                df = pd.DataFrame()

    # 3) Normalize columns when possible
    if not df.empty:
        rename_map = {
            'price_open': 'entry_price',
            'open_price': 'entry_price',
            'OpenPrice': 'entry_price',
            'entry': 'entry_price',
            'price_current': 'current_price',
            'current': 'current_price',
            'CurrentPrice': 'current_price',
            'bid': 'current_price',
            'profit': 'pnl',
            'unrealized_profit': 'pnl',
            'UnrealizedPL': 'pnl',
            'pl': 'pnl',
            'cmd': 'type',
            'position_type': 'type',
            'side': 'type',
            'instrument': 'symbol',
            'ticket': 'ticket_id',
            'order': 'ticket_id',
            'lots': 'volume',
            'volumeLots': 'volume',
        }
        existing_map = {k: v for k, v in rename_map.items() if k in df.columns}
        if existing_map:
            df.rename(columns=existing_map, inplace=True)

        for col in ('entry_price', 'current_price', 'pnl', 'volume'):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Map numeric → string; normalize strings
        if 'type' in df.columns:
            if pd.api.types.is_numeric_dtype(df['type']):
                df['type'] = df['type'].map({0: 'BUY', 1: 'SELL', 2: 'BUY', 3: 'SELL'}).fillna(df['type'])
            else:
                df['type'] = df['type'].astype(str).str.upper().replace({'LONG': 'BUY', 'SHORT': 'SELL'})

        # Derive missing essentials
        if 'current_price' not in df.columns:
            for alt in ('ask', 'Bid', 'Ask', 'last', 'LastPrice'):
                if alt in df.columns:
                    df['current_price'] = pd.to_numeric(df[alt], errors='coerce')
                    break
        if 'entry_price' not in df.columns:
            for alt in ('open', 'Open', 'avg_entry_price', 'AverageOpenPrice'):
                if alt in df.columns:
                    df['entry_price'] = pd.to_numeric(df[alt], errors='coerce')
                    break
        if 'symbol' not in df.columns:
            for alt in ('Symbol', 'SYMBOL', 'ticker', 'Ticker', 'symbolName'):
                if alt in df.columns:
                    df['symbol'] = df[alt]
                    break
        if 'pnl' not in df.columns and 'profit' in df.columns:
            df['pnl'] = pd.to_numeric(df['profit'], errors='coerce')

    return df

# --- HEADER & VITALS ---
render_market_header()

# --- REAL‑TIME ACCOUNT MONITORING & RISK CONTROL (from Risk Manager mock) ---
st.subheader("🔒 Real-Time Account Monitoring & Risk Control")

# Pull live account/risk, and positions count
acct = safe_api_call('GET', 'api/v1/account/info') or {}
risk = safe_api_call('GET', 'api/v1/account/risk') or {}

# Core numbers
bal = float(acct.get('balance', 0.0) or 0.0)
eq  = float(acct.get('equity', 0.0) or 0.0)
sod = float(risk.get('sod_equity', bal or eq) or 0.0)
loss_amt = float(risk.get('loss_amount', 0.0) or 0.0)

# Positions (use shared helper)
df_trades = _fetch_positions_df()
_positions_count = int(len(df_trades)) if not df_trades.empty else 0

# Today P&L and risk remaining
pnl_today = eq - sod
risk_left_amt = loss_amt - max(0.0, (sod - eq))  # remaining before breaching daily loss cap

# Margin snapshot (if provided by bridge/API)
_margin_used = float(acct.get('margin', 0.0) or 0.0)
_free_margin = float(acct.get('free_margin', 0.0) or 0.0)
_margin_level = acct.get('margin_level', None)
try:
    _margin_level_str = f"{float(_margin_level):,.0f}%" if _margin_level is not None else "—"
except Exception:
    _margin_level_str = "—"

# Drawdown vs SoD
try:
    dd_pct = max(0.0, ((sod - eq) / sod) * 100.0) if sod > 0 else 0.0
except Exception:
    dd_pct = 0.0

# --- Tiles row 1: Balance / Equity / P&L Today / Margin Used / Positions ---
row1 = st.columns([1,1,1,1,1])
with row1[0]:
    st.metric("Balance", f"${bal:,.0f}")
with row1[1]:
    st.metric("Equity", f"${eq:,.0f}")
with row1[2]:
    st.metric("P&L (Today)", f"${pnl_today:+,.0f}")
with row1[3]:
    st.metric("Margin Used", f"${_margin_used:,.0f}" if _margin_used else "—")
with row1[4]:
    st.metric("Positions Open", f"{_positions_count}")

# --- Tiles row 2: Free Margin / Margin Level / Risk Left / Drawdown ---
row2 = st.columns([1,1,1,1])
with row2[0]:
    st.metric("Free Margin", f"${_free_margin:,.0f}" if _free_margin else "—")
with row2[1]:
    st.metric("Margin Level", _margin_level_str)
with row2[2]:
    st.metric("Risk Left Today", (f"${risk_left_amt:,.0f}" if loss_amt else "—"))
with row2[3]:
    st.metric("Drawdown (SoD)", f"{dd_pct:.2f}%")

# Exposure alerting logic — if more than 5 positions
try:
    # Normalize floating PnL for alert text (fallback to sum of trade pnl if `acct.profit` missing)
    _dfp = df_trades.rename(columns={'profit':'pnl'}) if not df_trades.empty else pd.DataFrame()
    _pnl_sum = float(pd.to_numeric(_dfp.get('pnl'), errors='coerce').fillna(0).sum()) if not _dfp.empty else float(acct.get('profit') or 0.0)
except Exception:
    _pnl_sum = float(acct.get('profit') or 0.0)

if _positions_count > 5:
    if _pnl_sum < 0:
        st.error(f"⚠️ High exposure: {_positions_count} open positions with net loss {_pnl_sum:+.2f}")
    else:
        st.info(f"ℹ️ High exposure: {_positions_count} open positions (net profit {_pnl_sum:+.2f}).")


st.subheader("💰 Session Vitals")

try:
    mirror = safe_api_call('GET', 'api/v1/mirror/state') or {}
    # Use acct/risk as already fetched above
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
                center_title=f"{eq:,.0f}",
                center_sub=f"{pnl_today:+,.0f} today",
            ),
            use_container_width=True,
        )
    with cV2:
        st.plotly_chart(
            oneway_donut(
                title="Position Exposure",
                frac=max(0.0, min(1.0, exp_ratio)),
                center_title=f"{exp_ratio*100:.0f}%",
                center_sub="of daily risk budget",
            ),
            use_container_width=True,
        )
    with cV3:
        st.plotly_chart(
            oneway_donut(
                title="Behavioral Posture",
                frac=max(0.0, min(1.0, bhv_ratio)),
                center_title=f"{bhv_score:.0f}",
                center_sub="composite",
            ),
            use_container_width=True,
        )
        # Quick legend for meaning
        st.caption("Donuts: left = P&L vs SoD target/loss · middle = exposure vs daily risk budget · right = behavioral composite.")
except Exception as e:
    st.error(f"Could not load session vitals. Error: {e}")

# --- OPEN POSITIONS ---
st.subheader("📂 Open Positions")

# Debug: show which source responded (MT5 or which API endpoint)
try:
    _src = st.session_state.get('positions_source', '—')
    st.caption(f"Source: {_src}")
except Exception:
    pass

# Fetch positions (reuse shared helper; avoids duplicate bridge/API calls)
if 'df_trades' not in locals() or df_trades is None or getattr(df_trades, 'empty', True):
    df_trades = _fetch_positions_df()

if not df_trades.empty:
    # Standardize column names from different sources
    rename_map = {
        'price_open': 'entry_price',
        'profit': 'pnl',
        'price_current': 'current_price'
    }
    df_trades.rename(columns=rename_map, inplace=True)

    # Rescue fill for required columns if missing
    if 'entry_price' not in df_trades.columns:
        for alt in ('open','Open','avg_entry_price','AverageOpenPrice'):
            if alt in df_trades.columns:
                df_trades['entry_price'] = pd.to_numeric(df_trades[alt], errors='coerce')
                break
    if 'current_price' not in df_trades.columns:
        for alt in ('current','CurrentPrice','bid','ask','LastPrice'):
            if alt in df_trades.columns:
                df_trades['current_price'] = pd.to_numeric(df_trades[alt], errors='coerce')
                break
    if 'pnl' not in df_trades.columns:
        for alt in ('profit','unrealized_profit','UnrealizedPL','pl'):
            if alt in df_trades.columns:
                df_trades['pnl'] = pd.to_numeric(df_trades[alt], errors='coerce')
                break
    if 'type' in df_trades.columns and pd.api.types.is_numeric_dtype(df_trades['type']):
        df_trades['type'] = df_trades['type'].map({0:'BUY',1:'SELL',2:'BUY',3:'SELL'}).fillna(df_trades['type'])
    elif 'type' in df_trades.columns:
        df_trades['type'] = df_trades['type'].astype(str).str.upper().replace({'LONG':'BUY','SHORT':'SELL'})
    if 'symbol' not in df_trades.columns:
        for alt in ('Symbol','SYMBOL','instrument','ticker','Ticker','symbolName'):
            if alt in df_trades.columns:
                df_trades['symbol'] = df_trades[alt]
                break

    # Map position type from integer to string (for MT5 source)
    if 'type' in df_trades.columns and pd.api.types.is_numeric_dtype(df_trades['type']):
        df_trades['type'] = df_trades['type'].map({0: 'BUY', 1: 'SELL'})

    # Ensure all required columns are present
    required_cols = ['symbol', 'type', 'entry_price', 'current_price', 'pnl']
    if all(col in df_trades.columns for col in required_cols):
        # High‑exposure secondary alert (contextual to table)
        _pos_ct = len(df_trades)
        try:
            _pnl_total = float(pd.to_numeric(df_trades['pnl'], errors='coerce').fillna(0).sum())
        except Exception:
            _pnl_total = 0.0
        if _pos_ct > 5:
            if _pnl_total < 0:
                st.error(f"⚠️ High exposure: {_pos_ct} open positions with net loss {_pnl_total:+.2f}")
            else:
                st.info(f"ℹ️ High exposure: {_pos_ct} open positions (net profit {_pnl_total:+.2f}).")

        for idx, row in df_trades[required_cols].iterrows():
            cols = st.columns([2, 2, 2, 2, 2, 3])
            cols[0].write(row["symbol"])
            cols[1].write(row["type"])
            cols[2].write(f"{row['entry_price']:.5f}")
            cols[3].write(f"{row['current_price']:.5f}")
            pnl_color = "#22C55E" if row["pnl"] >= 0 else "#EF4444"
            cols[4].markdown(f"<div style='color:{pnl_color}; font-weight:bold'>{row['pnl']:+.2f}</div>", unsafe_allow_html=True)
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

