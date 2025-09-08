import streamlit as st
import json
from pathlib import Path
from dashboard.utils.streamlit_api import fetch_symbols as _api_fetch_symbols
from dashboard.utils.confluence_visuals import render_confluence_donut
import os
import time
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

# --- Symbols source + favorite default (API-driven) -------------------------
try:
    _symbols = _api_fetch_symbols() or []
except Exception:
    _symbols = []
if not _symbols:
    _symbols = ["EURUSD"]
symbol = st.selectbox("Symbol", _symbols, index=0)
st.session_state['pulse_fav_symbol'] = symbol
# Agent Ops — Quick Checklist (price integrity)
with st.expander("Price Confirmation Checklist", expanded=False):
    st.markdown(
        "- Confirm latest price via `/api/v1/feed/bars-enriched` (preferred)\n"
        "- If primary feed is down, use Yahoo chart API (e.g., `XAUUSD=X`, `GC=F`)\n"
        "- Never state a price if no feed is reachable\n"
        "- When quoting, include instrument + timeframe + time (e.g., M15 close at 13:45Z)"
    )
    st.caption("See full guidance in Agent Ops → GPT Instructions below.")

# Agent Ops — GPT Instructions (inline reference)
with st.expander("Agent Ops — GPT Instructions", expanded=False):
    try:
        from pathlib import Path
        p = Path(__file__).resolve().parents[2] / "docs" / "custom_gpt_instructions.md"
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        if text:
            st.markdown(text)
        else:
            st.info("Instructions file not found: docs/custom_gpt_instructions.md")
    except Exception:
        st.info("Unable to load instructions.")
    

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

with st.sidebar.expander("Confluence Weights", expanded=False):
    st.caption("Local override (applies to this view)")
    # Scope toggle: global (default) or symbol-specific
    sym_scope = st.checkbox(f"Symbol-specific ({symbol})", value=False, help="If enabled, save/load weights for this symbol only; otherwise global defaults.")
    def _w(key: str, default: float):
        return float(st.session_state.get(f'conf_w_{key}', default))
    w_context = st.slider("Context", 0.0, 1.0, value=_w('context', 0.2), step=0.05, key='conf_w_context')
    w_liq = st.slider("Liquidity", 0.0, 1.0, value=_w('liquidity', 0.2), step=0.05, key='conf_w_liquidity')
    w_struct = st.slider("Structure", 0.0, 1.0, value=_w('structure', 0.25), step=0.05, key='conf_w_structure')
    w_imb = st.slider("Imbalance", 0.0, 1.0, value=_w('imbalance', 0.15), step=0.05, key='conf_w_imbalance')
    w_risk = st.slider("Risk", 0.0, 1.0, value=_w('risk', 0.2), step=0.05, key='conf_w_risk')
    thr = st.slider("Threshold", 0.0, 1.0, value=float(st.session_state.get('conf_threshold', 0.6)), step=0.05, key='conf_threshold')
    # Show sum and normalization hint
    raw_sum = float(w_context + w_liq + w_struct + w_imb + w_risk)
    st.caption(f"Weights sum: {raw_sum:.2f} — normalized before sending to API")
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save as default"):
            try:
                payload = {
                    "weights": {
                        "context": float(st.session_state.get('conf_w_context', w_context)),
                        "liquidity": float(st.session_state.get('conf_w_liquidity', w_liq)),
                        "structure": float(st.session_state.get('conf_w_structure', w_struct)),
                        "imbalance": float(st.session_state.get('conf_w_imbalance', w_imb)),
                        "risk": float(st.session_state.get('conf_w_risk', w_risk)),
                    },
                    "threshold": float(st.session_state.get('conf_threshold', thr)),
                }
                if sym_scope and symbol:
                    payload["symbol"] = symbol
                r = requests.post(f"{base}/api/v1/feed/pulse-weights", json=payload, timeout=1.5)
                if r.ok:
                    st.success("Saved")
                else:
                    st.warning(f"Save failed: HTTP {r.status_code}")
            except Exception as e:
                st.warning(f"Save failed: {e}")
    with c2:
        if st.button("Load server defaults"):
            try:
                params = {"symbol": symbol} if sym_scope and symbol else None
                r = requests.get(f"{base}/api/v1/feed/pulse-weights", params=params, timeout=1.5)
                if r.ok:
                    data = r.json() or {}
                    w = data.get('weights') or {}
                    st.session_state['conf_w_context'] = float(w.get('context', 0.2))
                    st.session_state['conf_w_liquidity'] = float(w.get('liquidity', 0.2))
                    st.session_state['conf_w_structure'] = float(w.get('structure', 0.25))
                    st.session_state['conf_w_imbalance'] = float(w.get('imbalance', 0.15))
                    st.session_state['conf_w_risk'] = float(w.get('risk', 0.2))
                    st.session_state['conf_threshold'] = float(data.get('threshold', 0.6))
                    st.experimental_rerun()
                else:
                    st.warning(f"Load failed: HTTP {r.status_code}")
            except Exception as e:
                st.warning(f"Load failed: {e}")


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
        t0 = time.time()
        params = {"symbol": sym}
        # Pass local overrides to backend
        raw_ws = {}
        for k in ("context", "liquidity", "structure", "imbalance", "risk"):
            v = st.session_state.get(f'conf_w_{k}')
            if isinstance(v, (int, float)):
                raw_ws[k] = float(v)
        s = sum(raw_ws.values())
        if s > 0:
            for k, v in raw_ws.items():
                params[f"w_{k}"] = v / s
        thr = st.session_state.get('conf_threshold')
        if isinstance(thr, (int, float)):
            params["threshold"] = thr
        r = requests.get(f"{base}/api/v1/feed/pulse-status", params=params, timeout=1.5)
        if r.ok:
            out = r.json() or {}
            out['__latency_ms'] = int((time.time() - t0) * 1000)
            return out
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

lat_ms = status.get('__latency_ms') if isinstance(status, dict) else None
if isinstance(lat_ms, int):
    st.caption(f"Pulse API latency: {lat_ms} ms")

conf = status.get('confidence') if isinstance(status, dict) else None
if isinstance(conf, (int, float)):
    st.caption(f"Confluence confidence: {float(conf)*100:.1f}%")

# Confluence donut snapshot (lean, directly from status flags)
try:
    if isinstance(status, dict) and status:
        gate_order = ["context", "liquidity", "structure", "imbalance", "risk"]
        summary = {}
        for g in gate_order:
            v = status.get(g)
            if v is None:
                summary[g] = "missing"
            else:
                summary[g] = "passed" if int(v) == 1 else "failed"
        score = float(status.get('confidence') or 0.0)
        fig_conf = render_confluence_donut(summary, score)
        st.plotly_chart(fig_conf, use_container_width=True)
except Exception:
    pass

# Recent gate hits (lean view)
with st.expander("Recent Gate Hits", expanded=False):
    try:
        base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
        params = {"limit": 50, "symbol": symbol}
        r = requests.get(f"{base}/api/v1/feed/pulse-gate-hits", params=params, timeout=1.5)
        if r.ok:
            items = (r.json() or {}).get('items') or []
            if items:
                dfh = pd.DataFrame(items)
                cols = [c for c in ["timestamp", "symbol", "gate", "passed", "score"] if c in dfh.columns]
                st.dataframe(dfh[cols], use_container_width=True, height=180)
            else:
                st.caption("No recent events")
        else:
            st.caption("Feed unavailable")
    except Exception:
        st.caption("Feed unavailable")

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
