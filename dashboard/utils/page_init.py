import os
import streamlit as st
from typing import Tuple

from dashboard.utils.streamlit_api import fetch_symbols, inject_glass_css


def init_page(title: str, icon: str = "📊", layout: str = "wide", sidebar_state: str = "expanded") -> None:
    """Standard page initializer: set config and inject glass CSS."""
    try:
        st.set_page_config(page_title=title, page_icon=icon, layout=layout, initial_sidebar_state=sidebar_state)
    except Exception:
        # set_page_config may raise if called after other Streamlit calls
        pass
    try:
        inject_glass_css()
    except Exception:
        pass


def select_symbol(*, key_prefix: str = "sym", default_env: str = "PULSE_DEFAULT_SYMBOL") -> Tuple[str, list]:
    """Render a unified symbol selector using API symbols with an env default.

    Returns (selected_symbol, all_symbols)
    """
    try:
        symbols = fetch_symbols() or []
    except Exception:
        symbols = []
    if not symbols:
        symbols = [os.getenv(default_env, "XAUUSD").upper()]
    default_sym = os.getenv(default_env, "XAUUSD").upper()
    if default_sym not in symbols:
        default_sym = symbols[0]
    sym = st.selectbox("Symbol", symbols, index=symbols.index(default_sym) if default_sym in symbols else 0, key=f"{key_prefix}_select")
    return sym, symbols

