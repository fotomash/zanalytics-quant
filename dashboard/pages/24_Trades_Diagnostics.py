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

from dashboard.utils.streamlit_api import api_url, get_api_base, apply_custom_styling, fetch_symbols


st.set_page_config(page_title="Trade History", page_icon="🧪", layout="wide")
apply_custom_styling()

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

# --- Custom interactive table rendering (replaces st.dataframe) ---
cols_mt5 = ["id", "symbol", "direction", "entry", "exit", "pnl", "ts", "status"]
df_mt5_norm = _normalize_cols(df_mt5, cols_mt5)

# Render header
if not df_mt5_norm.empty:
    header_cols = st.columns([2, 2, 2, 2, 2, 2, 3])
    headers = ["Symbol", "Direction", "Entry", "Exit", "P&L", "Timestamp", "Actions"]
    for i, h in enumerate(headers):
        header_cols[i].markdown(f"**{h}**")

    for idx, row in df_mt5_norm.iterrows():
        cols = st.columns([2, 2, 2, 2, 2, 2, 3])
        # Defensive extraction
        trade_id = row.get("id", idx)
        cols[0].write(str(row.get("symbol", "")))
        cols[1].write(str(row.get("direction", "")))
        cols[2].write(str(row.get("entry", "")))
        cols[3].write(str(row.get("exit", "")))
        cols[4].write(str(row.get("pnl", "")))
        # Timestamp formatting
        ts_val = row.get("ts", "")
        ts_disp = str(ts_val)
        try:
            # try to parse and pretty print if possible
            if isinstance(ts_val, (int, float)):
                ts_disp = dt.datetime.fromtimestamp(ts_val).strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(ts_val, str):
                # try ISO parse
                ts_disp = str(pd.to_datetime(ts_val))
        except Exception:
            pass
        cols[5].write(ts_disp)
        # Actions column
        with cols[6]:
            st.button("SL → BE", key=f"slbe_{trade_id}")
            st.button("Trail 25%", key=f"trail25_{trade_id}")
            st.button("Trail 50%", key=f"trail50_{trade_id}")
            st.button("Partial 25%", key=f"partial25_{trade_id}")
            st.button("Partial 50%", key=f"partial50_{trade_id}")

