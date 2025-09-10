import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

from dashboard.utils.streamlit_api import safe_api_call

# ------------------------------------------------------------------
# basic page setup
# ------------------------------------------------------------------
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ROOT_ENV if _ROOT_ENV.exists() else None)

st.set_page_config(page_title="Macro & News", page_icon="📰", layout="wide")

st.title("Macro & News")

# ------------------------------------------------------------------
# API helpers
# ------------------------------------------------------------------

def pulse_health() -> Dict[str, Any]:
    return safe_api_call("GET", "pulse/health") or {}


def score_peek() -> Dict[str, Any]:
    return safe_api_call("POST", "score/peek") or {}


def risk_summary() -> Dict[str, Any]:
    return safe_api_call("GET", "risk/summary") or {}


def signals_top() -> Dict[str, Any]:
    return safe_api_call("GET", "signals/top?n=3") or {}


def adapter_status() -> Dict[str, Any]:
    return safe_api_call("GET", "adapter/status") or {}


def journal_recent() -> Dict[str, Any]:
    return safe_api_call("GET", "journal/recent?N=20") or {}


# ------------------------------------------------------------------
# Macro data with caching (15m TTL)
# ------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def fetch_macro() -> Dict[str, Any]:
    out: Dict[str, Any] = {"sp500": None, "gdp": None}
    try:
        out["sp500"] = yf.Ticker("^GSPC").info.get("regularMarketPrice")
    except Exception:
        pass
    try:
        fred_key = os.getenv("FRED_API_KEY")
        if fred_key:
            fred = Fred(api_key=fred_key)
            out["gdp"] = fred.get_series("GDP").iloc[-1]
    except Exception:
        pass
    return out


# ------------------------------------------------------------------
# Sidebar - API key status (masked)
# ------------------------------------------------------------------

with st.sidebar:
    st.header("API Status")
    fred_key = os.getenv("FRED_API_KEY")
    st.write(f"FRED_KEY: {'***' if fred_key else '—'}")
    st.write(f"DJANGO_API_URL: {os.getenv('DJANGO_API_URL', '—')}")


# ------------------------------------------------------------------
# Top tiles
# ------------------------------------------------------------------

score = score_peek()
risk = risk_summary()
health = pulse_health()
adapter = adapter_status()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Confluence", score.get("score", "—"))
col2.metric("Market Bias", score.get("bias", "—"))
col3.metric("Risk Remaining", risk.get("risk_left", "—"))
col4.metric("Suggested R:R", risk.get("suggested_rr", "—"))

# MIDAS health chip
if adapter:
    st.caption(
        f"MIDAS lag {adapter.get('lag','—')}ms • fps {adapter.get('fps','—')} • symbols {len(adapter.get('symbols', []) or [])}"
    )

# Kernel health caption
if health:
    st.caption(
        f"Kernel status: {health.get('status','—')} lag {health.get('lag','—')}ms"
    )


# ------------------------------------------------------------------
# Opportunities panel
# ------------------------------------------------------------------

st.subheader("Top Opportunities")
ops = signals_top().get("signals") or []
for sig in ops:
    with st.expander(f"{sig.get('symbol','?')} • {sig.get('bias','?')} • SL {sig.get('sl','?')} TP {sig.get('tp','?')}"):
        st.write(sig.get("reason", "No reason provided"))
        if sig.get("explain"):
            st.json(sig.get("explain"))


# ------------------------------------------------------------------
# Risk warnings/blocks
# ------------------------------------------------------------------

warnings = risk.get("warnings") or []
blocks = risk.get("blocks") or []
if warnings or blocks:
    st.subheader("Risk Warnings / Blocks")
    for w in warnings:
        st.warning(w)
    for b in blocks:
        st.error(b)


# ------------------------------------------------------------------
# Recent outcomes
# ------------------------------------------------------------------

recent = journal_recent().get("outcomes") or []
if recent:
    st.subheader("Recent Outcomes")
    st.dataframe(recent)


# ------------------------------------------------------------------
# Macro & News module
# ------------------------------------------------------------------

macro = fetch_macro()
with st.expander("Macro & News", expanded=True):
    cols = st.columns(2)
    cols[0].metric("US GDP", macro.get("gdp", "—"))
    cols[1].metric("S&P 500", macro.get("sp500", "—"))
    st.caption(f"Last refreshed {datetime.utcnow().isoformat()}Z")
