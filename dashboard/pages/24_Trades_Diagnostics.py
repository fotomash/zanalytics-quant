"""
Trades Diagnostics — quick sanity panel to verify trades/positions wiring.

Pulls from Django API endpoints and shows side‑by‑side views:
- DB: /api/v1/trades/recent
- MT5: /api/v1/trades/history?source=mt5
- Open Positions: /api/v1/account/positions
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

from dashboard.utils.streamlit_api import api_url, get_api_base, inject_glass_css


st.set_page_config(page_title="Trades Diagnostics", page_icon="🧪", layout="wide")
inject_glass_css()

st.markdown("### 🧪 Trades Diagnostics")
st.caption("Verify that DB trades, MT5 history, and open positions are flowing.")

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
    """
    Accepts either a list of row dicts or a dict payload that nests a list
    under common keys like results/items/trades/history/data/rows.
    """
    try:
        if isinstance(rows, list):
            return pd.DataFrame(rows)
        if isinstance(rows, dict):
            for key in ("results", "items", "trades", "history", "data", "rows"):
                val = rows.get(key)
                if isinstance(val, list):
                    return pd.DataFrame(val)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


cc1, cc2, cc3 = st.columns(3)
with cc1:
    limit = st.number_input("Recent trades (DB) limit", 1, 500, 50)
with cc2:
    date_from = st.date_input("MT5 date_from", value=(dt.date.today() - dt.timedelta(days=14)))
with cc3:
    show_raw = st.checkbox("Show raw JSON", value=False)


# Fetch endpoints
url_db = api_url("api/v1/trades/recent")
url_mt5 = api_url("api/v1/trades/history")
url_pos = api_url("api/v1/account/positions")

db_trades = _get_json(url_db, params={"limit": int(limit)})
mt5_trades = _get_json(
    url_mt5,
    params={"source": "mt5", "date_from": date_from.isoformat(), "date_to": dt.date.today().isoformat()}
)
positions = _get_json(url_pos)

# Fallback: some backends expect 'provider=mt5' instead of 'source=mt5'
if (isinstance(mt5_trades, dict) and not _as_df(mt5_trades).shape[0]):
    mt5_trades = _get_json(url_mt5, params={"provider": "mt5", "date_from": date_from.isoformat()})

df_db = _as_df(db_trades)
df_mt5 = _as_df(mt5_trades)
df_pos = _as_df(positions)


def _normalize_cols(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    miss = [c for c in cols if c not in df.columns]
    for c in miss:
        df[c] = None
    return df[cols]


st.markdown("#### Overview")
ov1, ov2, ov3 = st.columns(3)
with ov1:
    st.metric("DB Trades (recent)", len(df_db))
with ov2:
    st.metric("MT5 Trades (history)", len(df_mt5))
with ov3:
    st.metric("Open Positions", len(df_pos))


st.divider()
st.markdown("#### DB Trades (recent)")
if show_raw:
    st.json(db_trades)
cols_db = ["id", "symbol", "side", "entry", "exit", "pnl", "ts_open", "ts_close"]
st.dataframe(_normalize_cols(df_db, cols_db), use_container_width=True, height=260)

st.markdown("#### MT5 Trades (history)")
if show_raw:
    st.json(mt5_trades)
cols_mt5 = ["id", "symbol", "direction", "entry", "exit", "pnl", "ts", "status"]
st.dataframe(_normalize_cols(df_mt5, cols_mt5), use_container_width=True, height=260)

st.markdown("#### Open Positions")
if show_raw:
    st.json(positions)
cols_pos = ["ticket", "symbol", "type", "volume", "price_open", "sl", "tp", "price_current", "profit"]
st.dataframe(_normalize_cols(df_pos, cols_pos), use_container_width=True, height=260)


# Quick heuristics
st.divider()
st.markdown("#### Heuristics")
notes: List[str] = []
if df_db.empty and df_mt5.empty:
    notes.append("No trades detected from DB or MT5 — check MT5 bridge and DB sync.")
if not df_pos.empty and df_db.empty:
    notes.append("Open positions exist but DB trades view is empty — expected if trades are still open.")
if len(df_mt5) < len(df_db) and not df_db.empty:
    notes.append("MT5 history shorter than DB recent — date_from filter may exclude older trades.")
if df_pos.empty:
    notes.append("No open positions — if this is unexpected, confirm broker connection.")
if notes:
    for n in notes:
        st.info(n)
else:
    st.success("Trades and positions endpoints are returning data as expected.")

