"""
Zanalytics Pulse — Position Manager
A streamlined view of open positions with integrated actions.
"""
import streamlit as st
import pandas as pd
import os
import requests
import json
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎯 Zanalytics Pulse — Position Manager",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styling ---
def get_image_as_base64(path: str):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

img_base64 = get_image_as_base64("image_af247b.jpg")
if img_base64:
    background_style = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background-image: linear-gradient(rgba(0,0,0,0.80), rgba(0,0,0,0.80)), url(data:image/jpeg;base64,{img_base64});
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
    st.markdown(background_style, unsafe_allow_html=True)

# --- API UTILITIES ---
def get_api_base_url():
    return os.getenv("DJANGO_API_URL", "http://django:8000").rstrip('/')

def safe_api_call(method: str, path: str, payload: dict = None, timeout: float = 5.0) -> dict:
    """Safe API call with error handling."""
    base_url = get_api_base_url()
    url = f"{base_url}{path}" if path.startswith('/') else f"{base_url}/{path}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload or {}, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "url": url}

# --- DATA FETCHING ---
def fetch_positions() -> pd.DataFrame:
    """Fetch open positions from the backend."""
    data = safe_api_call("GET", "/api/v1/positions/live")
    if "error" in data or not isinstance(data, list):
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Normalize columns
    rename_map = {
        'price_open': 'entry_price', 'profit': 'pnl', 'price_current': 'current_price',
        'ticket': 'ticket_id', 'type': 'side'
    }
    df = df.rename(columns=rename_map)
    
    # Ensure essential columns exist
    for col in ['symbol', 'side', 'entry_price', 'current_price', 'pnl', 'volume', 'time', 'ticket_id']:
        if col not in df.columns:
            df[col] = None
            
    # Normalize side
    if 'side' in df.columns:
        df['side'] = df['side'].apply(lambda x: 'BUY' if x == 0 else 'SELL' if x == 1 else x)

    # Convert time
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
        
    return df

# --- ACTIONS ---
def close_position(ticket_id):
    """Send a request to close a position."""
    response = safe_api_call("POST", f"/api/v1/positions/{ticket_id}/close", payload={})
    if "error" in response:
        st.error(f"Failed to close position {ticket_id}: {response.get('error')}")
    else:
        st.success(f"Close order for position {ticket_id} sent successfully.")
        st.experimental_rerun()

# --- UI RENDERING ---
st.title("🛡️ Position Manager")

positions_df = fetch_positions()

if positions_df.empty:
    st.info("No open positions found.")
else:
    for _, row in positions_df.iterrows():
        with st.container():
            pnl = row.get('pnl', 0.0)
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_arrow = "🔼" if pnl >= 0 else "🔽"

            duration_str = "—"
            duration_color = "white"
            if pd.notna(row.get('time')):
                duration = datetime.utcnow() - row['time']
                duration_hours = duration.total_seconds() / 3600
                duration_str = str(duration).split('.')[0] # HH:MM:SS
                if duration_hours > 2:
                    duration_color = "red"
                elif duration_hours > 1:
                    duration_color = "orange"

            card_style = """
                <div style='
                    padding: 12px 16px;
                    border-radius: 10px;
                    background: rgba(40, 40, 50, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(5px);
                    margin-bottom: 10px;
                '>
            """
            st.markdown(card_style, unsafe_allow_html=True)

            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 4])

            with col1:
                st.markdown(f"""
                    <div style='font-weight: 600; font-size: 1.1em;'>{row.get('symbol', '—')}</div>
                    <div style='font-size: 0.9em; opacity: 0.8;'>{row.get('side', '—')} {row.get('volume', '')}</div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div style='font-size: 0.8em; opacity: 0.7;'>PnL</div>
                    <div style='color: {pnl_color}; font-weight: 600;'>
                        {pnl_arrow} {pnl:+.2f}
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div style='font-size: 0.8em; opacity: 0.7;'>Duration</div>
                    <div style='color: {duration_color};'>{duration_str}</div>
                """, unsafe_allow_html=True)
            
            with col4:
                 st.markdown(f"""
                    <div style='font-size: 0.8em; opacity: 0.7;'>Entry</div>
                    <div>{row.get('entry_price', 0.0):.5f}</div>
                """, unsafe_allow_html=True)

            with col5:
                btn_cols = st.columns(4)
                with btn_cols[0]:
                    st.button("SL>BE", key=f"slbe_{row.get('ticket_id')}", help="Move Stop Loss to Break Even (Not Implemented)")
                with btn_cols[1]:
                    st.button("T25%", key=f"t25_{row.get('ticket_id')}", help="Trail Stop Loss by 25% (Not Implemented)")
                with btn_cols[2]:
                    st.button("T50%", key=f"t50_{row.get('ticket_id')}", help="Trail Stop Loss by 50% (Not Implemented)")
                with btn_cols[3]:
                    if st.button("Close", key=f"close_{row.get('ticket_id')}"):
                        close_position(row.get('ticket_id'))
            
            st.markdown("</div>", unsafe_allow_html=True)

if st.button("Refresh"):
    st.experimental_rerun()