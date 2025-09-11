import os
from typing import List, Tuple, Dict, Any
import requests
import streamlit as st


@st.cache_data(ttl=30)
def fetch_symbols_list() -> List[str]:
    """Fetch available symbols from the backend; fallback to a common set."""
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    try:
        r = requests.get(f"{base}/api/v1/market/symbols", timeout=1.5)
        if r.ok:
            data = r.json() or {}
            syms = (data.get('symbols') if isinstance(data, dict) else None) or []
            syms = [str(s).upper() for s in syms if isinstance(s, str)]
            if syms:
                return syms
    except Exception:
        pass
    return ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "US500", "SPX500"]


def favorite_default(symbols: List[str]) -> str:
    """Resolve the default favorite symbol from session/env/list."""
    fav_default = os.getenv('PULSE_DEFAULT_SYMBOL', 'XAUUSD').upper()
    fav = (st.session_state.get('pulse_fav_symbol') or fav_default).upper()
    if symbols:
        return fav if fav in symbols else symbols[0]
    return fav


def render_favorite_selector(*, key: str) -> Tuple[List[str], str]:
    """Render the sidebar Settings expander with a Favorite symbol selector.

    Returns (symbols_list, selected_favorite).
    """
    with st.sidebar.expander("Settings", expanded=False):
        symbols = fetch_symbols_list()
        fav = favorite_default(symbols)
        # Try to load persisted favorite from backend
        try:
            base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
            r = requests.get(f"{base}/api/v1/user/prefs", timeout=1.2)
            if r.ok:
                data = r.json() or {}
                pfav = str(data.get('favorite_symbol') or '').upper()
                if pfav and pfav in symbols:
                    fav = pfav
        except Exception:
            pass
        idx = symbols.index(fav) if fav in symbols else 0
        fav_symbol = st.selectbox("Favorite symbol", symbols, index=idx, key=key)
        st.session_state['pulse_fav_symbol'] = fav_symbol
        # Persist favorite to backend
        try:
            base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
            requests.post(f"{base}/api/v1/user/prefs", json={"favorite_symbol": fav_symbol}, timeout=1.2)
        except Exception:
            pass
        return symbols, fav_symbol
