import time
import streamlit as st
from dashboard.utils.streamlit_api import safe_api_call

st.set_page_config(page_title="🎯 Live Confluence Monitor", page_icon="🎯", layout="wide")
st.title("🎯 Live Confluence Monitor")


def fetch_pulse_status(symbol: str) -> dict:
    """Pull Pulse status for a symbol (confidence + gates)."""
    data = safe_api_call('GET', f'api/v1/feed/pulse-status?symbol={symbol}') or {}
    return data if isinstance(data, dict) else {}


def fetch_risk_state() -> dict:
    """Pull current session risk envelope (SoD, targets, used_pct, exposure)."""
    rk = safe_api_call('GET', 'api/v1/account/risk') or {}
    return rk if isinstance(rk, dict) else {}


def grade_from_conf(conf: float | None) -> str:
    if not isinstance(conf, (int, float)):
        return "—"
    pct = conf * 100.0
    if pct >= 80:
        return "A"
    if pct >= 60:
        return "B"
    if pct >= 40:
        return "C"
    return "D"


col1, col2, col3 = st.columns(3)
symbols = ["XAUUSD", "EURUSD", "GBPUSD"]
placeholders = [col1.empty(), col2.empty(), col3.empty()]

for i, symbol in enumerate(symbols):
    st_status = fetch_pulse_status(symbol)
    conf = st_status.get('confidence') if isinstance(st_status, dict) else None
    if isinstance(conf, (int, float)):
        pct = float(conf) * 100.0
        placeholders[i].metric(label=symbol, value=f"{pct:.1f}%", delta=f"Grade: {grade_from_conf(conf)}")
    else:
        placeholders[i].metric(label=symbol, value="—", delta="Grade: —")

risk = fetch_risk_state()
used = risk.get('used_pct')
exposure = risk.get('exposure_pct')
def _norm(x):
    try:
        x = float(x)
        return x if x <= 1.0 else x/100.0
    except Exception:
        return None
st.sidebar.metric("Risk Used", f"{(_norm(used)*100):.0f}%" if _norm(used) is not None else "—")
st.sidebar.metric("Exposure", f"{(_norm(exposure)*100):.0f}%" if _norm(exposure) is not None else "—")

# Optional auto-refresh
auto = st.sidebar.checkbox("Auto-refresh", value=False)
interval = st.sidebar.slider("Interval (sec)", min_value=5, max_value=60, value=10, step=5)
if auto:
    time.sleep(interval)
    st.experimental_rerun()
