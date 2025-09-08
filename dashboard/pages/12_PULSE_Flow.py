import streamlit as st
import json
from pathlib import Path
from dashboard.utils.user_prefs import fetch_symbols_list
import os
import requests
import pandas as pd

st.set_page_config(page_title="PULSE Predictive Flow", page_icon="🧠", layout="wide")
st.title("PULSE Predictive Flow Framework")

# Load playbook JSON
def load_playbook():
    try:
        # Try multiple candidate paths: env var, relative to this file, repo root
        cand = []
        envp = os.getenv('PULSE_PLAYBOOK_PATH')
        if envp:
            cand.append(Path(envp))
        here = Path(__file__).resolve()
        cand.append((here.parents[2] / 'config' / 'playbooks' / 'pulse_v1.json'))  # repo root
        cand.append((here.parents[0] / 'pulse_v1.json'))  # same dir (unlikely)
        cand.append(Path('config/playbooks/pulse_v1.json'))  # CWD based
        for p in cand:
            try:
                if Path(p).exists():
                    with open(p, 'r') as f:
                        return json.load(f)
            except Exception:
                continue
        # Fallback: embedded minimal playbook
        return {
            "id": "pulse_v1",
            "name": "PULSE Predictive Flow Framework",
            "version": "1.0.0",
            "gates": [
                {"id": "context", "name": "Context Gate", "rule": "HTF bias aligns with POI & session", "optional": False},
                {"id": "liquidity", "name": "Liquidity Gate", "rule": "Asian/swing sweep then snap-back", "optional": False},
                {"id": "structure", "name": "Structure Gate", "rule": "M1 CHoCH on impulse vol ≥1.5× median", "optional": False},
                {"id": "imbalance", "name": "Imbalance Gate", "rule": "FVG/LPS from flip impulse; entry zone ±50%", "optional": False},
                {"id": "risk", "name": "Risk Gate", "rule": "Stop at swing ±3 pips; targets 1R/2R/3R", "optional": False},
                {"id": "confluence", "name": "Confluence Gate", "rule": "Weighted enhancers; size down if <0.75", "optional": True},
            ],
        }
    except Exception as e:
        st.warning(f"Unable to load playbook: {e}")
        return {"gates": []}

playbook = load_playbook()

# --- Symbols source + favorite default -------------------------------------
    

# Settings: favorite symbol (session + optional env)
with st.sidebar.expander("Settings", expanded=False):
    all_symbols = fetch_symbols_list()
    fav_default = os.getenv('PULSE_DEFAULT_SYMBOL', 'XAUUSD').upper()
    fav_symbol = st.session_state.get('pulse_fav_symbol', fav_default)
    fav_symbol = st.selectbox("Favorite symbol", all_symbols, index=all_symbols.index(fav_symbol) if fav_symbol in all_symbols else 0)
    st.session_state['pulse_fav_symbol'] = fav_symbol

# Symbol selector (use favorite as default; URL param overrides)
all_symbols = fetch_symbols_list()
sym_qp = st.experimental_get_query_params().get('sym', [None])[0]
default_sym = (sym_qp or st.session_state.get('pulse_fav_symbol') or os.getenv('PULSE_DEFAULT_SYMBOL', 'XAUUSD')).upper()
if default_sym not in all_symbols:
    default_sym = all_symbols[0] if all_symbols else 'XAUUSD'
symbol = st.selectbox("Symbol", all_symbols, index=all_symbols.index(default_sym) if default_sym in all_symbols else 0)
try:
    st.experimental_set_query_params(sym=symbol)
except Exception:
    pass

# Gate table (human narrative)
if playbook.get("gates"):
    gate_df = pd.DataFrame([
        {"Gate": g.get("name"), "Rule": g.get("rule"), "Optional": g.get("optional", False)}
        for g in playbook["gates"]
    ])
    st.dataframe(gate_df, use_container_width=True)
else:
    st.info("No gates found in playbook.")

st.divider()
st.subheader("Live Status")

def fetch_status(sym: str):
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    try:
        r = requests.get(f"{base}/api/v1/feed/pulse-status", params={"symbol": sym}, timeout=1.5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

status = fetch_status(symbol)
cols = st.columns(max(1, len(playbook.get("gates", []))))
for col, gate in zip(cols, playbook.get("gates", [])):
    state = status.get(gate.get("id"), 0)
    color = "#00cc96" if state else "#ef553b"
    label = gate.get("name") or gate.get("id")
    col.markdown(
        f"<div style='text-align:center; font-weight:600; color:{color}'>"
        f"{label}<br>●</div>",
        unsafe_allow_html=True
    )

# If backend is unreachable, provide a clear hint but keep UI usable
if not status:
    st.info("Live status unavailable — showing framework layout only. Ensure DJANGO_API_URL is reachable.")

# Optional: show Structure details under the lights
try:
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    r = requests.get(f"{base}/api/v1/feed/pulse-detail", params={"symbol": symbol}, timeout=1.5)
    if r.ok:
        details = r.json() or {}
        struct = details.get('structure') or {}
        if isinstance(struct, dict) and struct.get('impulse_volume') is not None:
            st.caption(
                f"Structure: {struct.get('direction') or '—'} | "
                f"CHoCH: {struct.get('choch_price') if struct.get('choch_price') is not None else '—'} | "
                f"BoS: {struct.get('bos_price') if struct.get('bos_price') is not None else '—'} "
                f"| Vol: {float(struct.get('impulse_volume') or 0):,.0f}/"
                f"{float(struct.get('median_volume') or 0):,.0f}"
            )
        liq = details.get('liquidity') or {}
        if isinstance(liq, dict) and (liq.get('sweep_type') or liq.get('direction')):
            st.caption(
                f"Liquidity: {liq.get('sweep_type') or '—'} • {liq.get('direction') or '—'}"
                + (f" • Snap-back: {liq.get('snapback_ts')}" if liq.get('snapback_ts') else "")
            )
        rsk = details.get('risk') or {}
        if isinstance(rsk, dict) and rsk.get('passed'):
            tgs = rsk.get('targets') or []
            tg_str = ", ".join(f"{t:,.4f}" for t in tgs[:3]) if tgs else "—"
            st.caption(
                f"Risk: entry {rsk.get('entry') or '—'} • stop {rsk.get('stop') or '—'} • targets {tg_str}"
            )
except Exception:
    pass
