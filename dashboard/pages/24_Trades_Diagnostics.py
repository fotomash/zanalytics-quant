"""
Trade History — streamlined view focused solely on MT5 trade history.

Queries:
- MT5 History: /api/v1/trades/history?source=mt5
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

from dashboard.utils.streamlit_api import api_url, get_api_base, inject_glass_css, fetch_symbols


st.set_page_config(page_title="Trade History", page_icon="🧪", layout="wide")
inject_glass_css()

st.markdown("### 🧪 Trade History")
st.caption("Explore MT5 trade history with symbol and date filters.")

# Symbol scope (consistent with other pages)
_symbols = fetch_symbols() or []
if 'diag_symbol' not in st.session_state:
    st.session_state['diag_symbol'] = (_symbols[0] if _symbols else 'XAUUSD')
sel_sym = st.selectbox(
    "Symbol",
    _symbols or ['XAUUSD'],
    index=(_symbols.index(st.session_state['diag_symbol']) if (_symbols and st.session_state['diag_symbol'] in _symbols) else 0),
    key="diag_symbol"
)
symbol = st.session_state.get('diag_symbol', 'XAUUSD')

with st.expander("API Base Settings", expanded=False):
    base = get_api_base()
    st.write(f"Resolved API base: {base}")
    st.info("Override API base under Advanced (if your env differs).")


def _get_json(url: str, *, params: Dict[str, Any] | None = None, timeout: float = 3.0):
    try:
        r = requests.get(url, params=params or {}, timeout=timeout)
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}", "url": url, "text": r.text}
    except Exception as e:
        return {"error": str(e), "url": url}


def _as_df(rows: List[Dict[str, Any]] | Any) -> pd.DataFrame:
    """Accept list OR dict containers like {'results': [...]}, {'data': [...]}, {'items': [...]}, {'history': [...]}, or {'rows': [...]}."""
    try:
        if isinstance(rows, list):
            return pd.DataFrame(rows)
        if isinstance(rows, dict):
            for key in ("results", "data", "items", "history", "rows"):
                val = rows.get(key)
                if isinstance(val, list):
                    return pd.DataFrame(val)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


cc1, cc2, cc3 = st.columns(3)
with cc1:
    date_from = st.date_input("From", value=(dt.date.today() - dt.timedelta(days=14)))
with cc2:
    date_to = st.date_input("To", value=dt.date.today())
with cc3:
    show_raw = st.checkbox("Show raw JSON", value=False)


url_mt5 = api_url("api/v1/trades/history")
mt5_params = {
    "source": "mt5",
    "date_from": date_from.isoformat(),
    "date_to": date_to.isoformat(),
    "symbol": symbol,
}
mt5_trades = _get_json(url_mt5, params=mt5_params)

# Fallback: some backends expect 'provider=mt5' instead of 'source=mt5'
if isinstance(mt5_trades, dict) and not _as_df(mt5_trades).shape[0]:
    mt5_trades = _get_json(
        url_mt5,
        params={
            "provider": "mt5",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "symbol": symbol,
        },
    )

df_mt5 = _as_df(mt5_trades)

if not df_mt5.empty and 'symbol' in df_mt5.columns:
    df_mt5 = df_mt5[df_mt5['symbol'] == symbol]

# Surface any API errors
if isinstance(mt5_trades, dict) and "error" in mt5_trades:
    st.warning(f"MT5 History error: {mt5_trades.get('error')} — {mt5_trades.get('url','')}")


def _normalize_cols(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    miss = [c for c in cols if c not in df.columns]
    for c in miss:
        df[c] = None
    return df[cols]


st.markdown(
    f"#### MT5 Trades (history) · <span style='color:#9CA3AF'>Symbol:</span> <span style='font-weight:700'>{symbol}</span>",
    unsafe_allow_html=True,
)
if show_raw:
    st.json(mt5_trades)
cols_mt5 = ["id", "symbol", "direction", "entry", "exit", "pnl", "ts", "status"]
st.dataframe(_normalize_cols(df_mt5, cols_mt5), use_container_width=True, height=260)

