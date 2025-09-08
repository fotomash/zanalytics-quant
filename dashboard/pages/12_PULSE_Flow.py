import streamlit as st
import json
from pathlib import Path
from dashboard.utils.streamlit_api import fetch_symbols as _api_fetch_symbols
from dashboard.utils.confluence_visuals import render_confluence_donut
import os
import time
import math
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
 

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

# ---------------------------------------------------------------------------
# Enhancements: Pac-Man donut, correlated watchboard, trades panel
# ---------------------------------------------------------------------------

DJ_API = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')

def _safe_get_json(url: str, *, params: dict | None = None, timeout: float = 2.0):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

def fetch_pulse_detail(sym: str) -> dict:
    return _safe_get_json(f"{DJ_API}/api/v1/feed/pulse-detail", params={"symbol": sym}, timeout=1.5) or {}

def build_gate_map(pulse_status: dict, pulse_detail: dict) -> list[dict]:
    weights = (pulse_status or {}).get("weights", {})
    flags   = {k: bool(v) for k, v in (pulse_status or {}).items() if k in {"context","liquidity","structure","imbalance","risk"}}
    # Derive per-gate detail if present
    detail_by_gate = {
        "context": (pulse_detail or {}).get("context") or {},
        "liquidity": (pulse_detail or {}).get("liquidity") or {},
        "structure": (pulse_detail or {}).get("structure") or {},
        "imbalance": (pulse_detail or {}).get("imbalance") or {},
        "risk": (pulse_detail or {}).get("risk") or {},
    }
    gates = []
    for gate in ["context","liquidity","structure","imbalance","risk"]:
        d = detail_by_gate.get(gate, {})
        gates.append({
            "gate": gate,
            "weight": float(weights.get(gate, 0.0) or 0.0),
            "passed": bool(flags.get(gate, False)),
            "score": float(d.get("score") or (1.0 if flags.get(gate) else 0.0)),
            "explain": d.get("explain") or "—",
            "evidence": d if isinstance(d, dict) else {},
        })
    return gates

def plot_pulse_pacman(sym: str, pulse_status: dict, gates: list[dict]):
    labels  = [sym] + [g["gate"].title() for g in gates]
    parents = [""]  + [sym for _ in gates]
    # Avoid zero total by ensuring non-zero root value
    values  = [max(1.0, sum(max(0.01, g["weight"]) for g in gates)*100.0)] + [max(0.01, g["weight"]) * 100.0 for g in gates]

    def gate_color(g):
        if g["passed"] and g["score"] >= 0.7: return "#22C55E"
        if g["passed"] and g["score"] >= 0.4: return "#F59E0B"
        return "#EF4444"

    colors = ["#0f172a"] + [gate_color(g) for g in gates]
    custom = [""]
    for g in gates:
        txt = (
            f"Gate: {g['gate']}\n"
            f"Weight: {g['weight']:.2f}\n"
            f"Score: {g['score']:.2f}\n"
            f"Passed: {g['passed']}\n"
            f"{g['explain']}"
        )
        custom.append(txt)

    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(colors=colors, line=dict(color="#0e1117", width=1)),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=custom,
    ))
    conf = float(pulse_status.get("confidence", 0.0) or 0.0)
    fig.update_layout(
        height=280,
        margin=dict(t=10, l=0, r=0, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"{int(conf*100)}%", x=0.5, y=0.5, showarrow=False, font=dict(size=20, color="#fff"))],
    )
    return fig

def _load_bars(symbol: str, timeframe: str = "M15", limit: int = 300) -> pd.DataFrame:
    data = _safe_get_json(f"{DJ_API}/api/v1/feed/bars-enriched", params={"symbol": symbol, "timeframe": timeframe, "limit": limit}, timeout=2.0) or {}
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return pd.DataFrame()
    df = pd.DataFrame(items)
    # Normalize
    for c in ["open","high","low","close","volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df

def _choose_correlated(base_symbol: str, universe: list[str], timeframe: str = "M15", n: int = 6) -> list[str]:
    series = {}
    for s in [base_symbol] + [u for u in universe if u != base_symbol]:
        try:
            df = _load_bars(s, timeframe=timeframe, limit=400)
            if not df.empty and "close" in df.columns:
                series[s] = df.set_index("timestamp")["close"].astype(float)
        except Exception:
            continue
    if base_symbol not in series:
        return []
    aligned = pd.concat(series.values(), axis=1, join="inner")
    aligned.columns = list(series.keys())
    rets = aligned.pct_change().dropna()
    if rets.empty:
        return []
    corrs = rets.corr()[base_symbol].sort_values(ascending=False)
    return [s for s in corrs.index if s != base_symbol][:n]

def render_correlated_watchboard(base_symbol: str):
    st.subheader("🧭 Correlated Watchboard")
    try:
        universe = _api_fetch_symbols() or []
    except Exception:
        universe = []
    if not universe:
        st.info("No universe available.")
        return
    picks = _choose_correlated(base_symbol, universe, timeframe="M15", n=6)
    if not picks:
        st.info("No correlated symbols found or data unavailable.")
        return
    cols = st.columns(min(3, len(picks)))
    for i, sym in enumerate(picks):
        ps = fetch_status(sym)
        pdz = fetch_pulse_detail(sym)
        gates = build_gate_map(ps or {}, pdz or {})
        fig = plot_pulse_pacman(sym, ps or {}, gates)
        with cols[i % len(cols)]:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            if st.button(f"Focus {sym}", key=f"focus_{sym}"):
                try:
                    st.session_state['pulse_fav_symbol'] = sym
                    st.experimental_set_query_params(sym=sym)
                except Exception:
                    pass
                st.experimental_rerun()

SESSIONS = {
    "Asian":   {"start": 21, "end": 24},
    "London":  {"start": 7,  "end": 10},
    "New_York":{"start": 13, "end": 16},
}

def _session_window_utc(name: str, ref: datetime | None = None):
    ref = ref or datetime.utcnow()
    h1, h2 = SESSIONS[name]["start"], SESSIONS[name]["end"]
    start = ref.replace(hour=h1, minute=0, second=0, microsecond=0)
    end   = ref.replace(hour=h2, minute=0, second=0, microsecond=0)
    if ref < end:
        start -= timedelta(days=1)
        end   -= timedelta(days=1)
    return pd.to_datetime(start, utc=True), pd.to_datetime(end, utc=True)

def _fetch_trades(limit: int = 200) -> pd.DataFrame:
    # Prefer recent endpoint if available; fallback to history
    data = _safe_get_json(f"{DJ_API}/api/v1/trades/recent", params={"limit": limit}, timeout=2.0)
    if not isinstance(data, list):
        data = _safe_get_json(f"{DJ_API}/api/v1/trades/history", params={"limit": limit}, timeout=2.0)
    data = data or []
    df = pd.DataFrame(data if isinstance(data, list) else [])
    for col in ("ts_open","ts_close"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    # Backfill ts_open from ts if needed
    if 'ts_open' not in df.columns and 'ts' in df.columns:
        try:
            df['ts_open'] = pd.to_datetime(df['ts'], errors='coerce', utc=True)
        except Exception:
            pass
    for col in ("pnl","rr","entry","exit"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def _compute_trade_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return dict(win_rate=0.0, pnl=0.0, wins=0, losses=0, avg_rr=float("nan"))
    pnl = float(df.get("pnl", pd.Series(dtype=float)).sum()) if "pnl" in df.columns else 0.0
    wins = int((df.get("pnl", pd.Series(dtype=float)) > 0).sum()) if "pnl" in df.columns else 0
    losses = int((df.get("pnl", pd.Series(dtype=float)) <= 0).sum()) if "pnl" in df.columns else 0
    total = max(1, wins + losses)
    win_rate = round(100.0 * wins / total, 1)
    avg_rr = float(df.get("rr", pd.Series(dtype=float)).replace([np.inf,-np.inf], np.nan).dropna().mean()) if "rr" in df.columns else float("nan")
    return dict(win_rate=win_rate, pnl=pnl, wins=wins, losses=losses, avg_rr=avg_rr)

def render_trades_panel():
    st.subheader("📒 Trades Overview (experimental)")
    df = _fetch_trades(limit=300)
    k = _compute_trade_kpis(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Win Rate", f"{k['win_rate']}%")
    c2.metric("Net PnL", f"{k['pnl']:+.2f}")
    c3.metric("Wins", k['wins'])
    c4.metric("Losses", k['losses'])
    c5.metric("Avg R:R", f"{k['avg_rr']:.2f}" if not math.isnan(k['avg_rr']) else "—")
    session_choice = st.selectbox("Session filter", ["All","Asian","London","New_York"], index=1)
    df_view = df.copy()
    if session_choice != "All" and not df_view.empty and "ts_open" in df_view.columns:
        s, e = _session_window_utc({"Asian":"Asian","London":"London","New_York":"New_York"}[session_choice])
        df_view = df_view[(df_view["ts_open"] >= s) & (df_view["ts_open"] <= e)].copy()
    st.markdown("### ⏱ Last Session Entries")
    if not df_view.empty:
        cols = [c for c in ["ts_open","symbol","side","entry","exit","pnl","rr","strategy","session"] if c in df_view.columns]
        st.dataframe(df_view.sort_values("ts_open", ascending=False)[cols].head(30), use_container_width=True)
    else:
        st.info("No trades in the selected session.")
    st.markdown("### 📌 Open Positions")
    try:
        pos = _safe_get_json(f"{DJ_API}/api/v1/account/positions", timeout=1.5) or []
        if isinstance(pos, list) and pos:
            dfp = pd.DataFrame(pos)
            c = [x for x in ["ticket","symbol","type","volume","price_open","sl","tp","profit"] if x in dfp.columns]
            st.dataframe(dfp[c], use_container_width=True)
        else:
            st.caption("No open positions.")
    except Exception as e:
        st.caption(f"Positions unavailable: {e}")

# Render Pac-Man donut for selected symbol
try:
    pdz = fetch_pulse_detail(symbol)
    gates = build_gate_map(status or {}, pdz or {})
    fig_pm = plot_pulse_pacman(symbol, status or {}, gates)
    st.markdown("### Confluence Pac‑Man")
    st.plotly_chart(fig_pm, use_container_width=True, config={"displayModeBar": False})
except Exception:
    pass

render_correlated_watchboard(symbol)
render_trades_panel()

# ---------------- Behavioral Compass & Panels -----------------
def fetch_behavior_events():
    return _safe_get_json(f"{DJ_API}/api/v1/behavior/events/today", timeout=2.0) or []

def fetch_equity_today():
    return _safe_get_json(f"{DJ_API}/api/v1/equity/today", timeout=2.0) or []

def _today_window(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or 'ts_open' not in df.columns:
        return df
    start = pd.Timestamp.utcnow().tz_localize('UTC').normalize()
    return df[df['ts_open'] >= start].copy()

def compute_patience_index(trades_df: pd.DataFrame, lookback_days: int = 7) -> dict:
    if trades_df.empty or 'ts_open' not in trades_df.columns:
        return dict(score=float('nan'), delta_pct=0, baseline_s=0, current_s=0)
    df = trades_df.sort_values('ts_open').copy()
    df['gap'] = df['ts_open'].diff().dt.total_seconds()
    baseline_cut = pd.Timestamp.utcnow().tz_localize('UTC').normalize()
    base = df[df['ts_open'] < baseline_cut]
    baseline = float(base['gap'].median()) if not base.empty else float('nan')
    today = _today_window(df)
    current = float(today['gap'].tail(3).median()) if not today.empty else float('nan')
    if not (baseline and baseline > 0) or not current:
        return dict(score=float('nan'), delta_pct=0, baseline_s=baseline or 0, current_s=current or 0)
    delta = (current - baseline) / baseline
    import numpy as _np
    score = float(_np.clip(50 + 50 * _np.tanh(delta), 0, 100))
    return dict(score=score, delta_pct=100*delta, baseline_s=baseline, current_s=current)

def compute_conviction_rates(trades_df: pd.DataFrame, high_thresh: float = 0.7) -> dict:
    if trades_df.empty:
        return dict(hc_win=0.0, lc_win=0.0, counts=(0,0))
    if 'conviction' in trades_df.columns:
        hc = trades_df[trades_df['conviction'].astype(str).str.lower()=='high']
        lc = trades_df[trades_df['conviction'].astype(str).str.lower()!='high']
    elif 'pulse_conf_at_entry' in trades_df.columns:
        hc = trades_df[trades_df['pulse_conf_at_entry'].astype(float) >= high_thresh]
        lc = trades_df[trades_df['pulse_conf_at_entry'].astype(float) <  high_thresh]
    else:
        if 'rr' in trades_df.columns:
            thr = trades_df['rr'].median()
            hc = trades_df[trades_df['rr'] >= thr]
            lc = trades_df[trades_df['rr'] < thr]
        else:
            hc = trades_df.iloc[:0]
            lc = trades_df
    def _win_rate(d: pd.DataFrame) -> float:
        if d.empty or 'pnl' not in d.columns:
            return 0.0
        n = len(d); w = int((d['pnl'] > 0).sum())
        return (w / n) if n else 0.0
    return dict(hc_win=_win_rate(hc), lc_win=_win_rate(lc), counts=(len(hc), len(lc)))

def compute_profit_efficiency(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return dict(avg=float('nan'))
    rr = trades_df['rr'] if 'rr' in trades_df.columns else pd.Series(dtype=float)
    mfe = trades_df['mfe_rr'] if 'mfe_rr' in trades_df.columns else rr.abs()
    eff = []
    for r, m in zip(rr.fillna(0), mfe.replace(0, pd.NA).fillna(pd.NA)):
        try:
            val = float(max(0.0, min(1.0, (r / m) if m and m != 0 else 0.0)))
            eff.append(val)
        except Exception:
            continue
    avg = float(pd.Series(eff).mean()) if eff else float('nan')
    return dict(avg=avg)

def compute_discipline_score(trades_today: pd.DataFrame, events_today: list, conf_thresh: float = 0.6) -> float:
    import numpy as _np
    if (trades_today is None or trades_today.empty) and not events_today:
        return float('nan')
    score = 100.0
    penalties = {"oversize": 25, "low_confluence_trade": 15, "cooldown_violation": 20, "overtrading": 10, "revenge_trade": 20, "chasing": 10}
    if 'pulse_conf_at_entry' in (trades_today.columns if trades_today is not None else []):
        try:
            low_conf = int((trades_today['pulse_conf_at_entry'].astype(float) < conf_thresh).sum())
            score -= low_conf * penalties['low_confluence_trade']
        except Exception:
            pass
    for e in (events_today or []):
        t = str(e.get('type') or '').lower()
        w = float(e.get('weight') or penalties.get(t, 10))
        score -= w
    return float(max(0.0, min(100.0, score)))

def plot_behavioral_compass(metrics: dict):
    disc = float(metrics.get('discipline') or float('nan'))
    pat  = float(metrics.get('patience_score') or float('nan'))
    pe   = float(metrics.get('profit_eff') or float('nan'))
    hc_w = float(metrics.get('hc_win') or 0.0)
    lc_w = float(metrics.get('lc_win') or 0.0)
    green, red, amber, blue, gray = "#22C55E", "#EF4444", "#F59E0B", "#3B82F6", "#374151"
    fig = go.Figure()
    if not math.isnan(disc):
        fig.add_trace(go.Pie(values=[max(0.1, disc), max(0.1, 100-disc)], labels=['Discipline',''], hole=0.55, sort=False, textinfo='none', marker=dict(colors=[green, 'rgba(255,255,255,0.05)']), hovertemplate=f"Discipline: {disc:.0f}%<extra></extra>", domain=dict(x=[0,1], y=[0,1])))
    if not math.isnan(pat):
        color = blue if pat >= 50 else amber
        fig.add_trace(go.Pie(values=[max(0.1, pat), max(0.1, 100-pat)], labels=['Patience',''], hole=0.65, sort=False, textinfo='none', marker=dict(colors=[color, 'rgba(255,255,255,0.05)']), hovertemplate=f"Patience: {pat:.0f}<extra></extra>", domain=dict(x=[0,1], y=[0,1])))
    if not math.isnan(pe):
        pe_pct = 100*pe
        fig.add_trace(go.Pie(values=[max(0.1, pe_pct), max(0.1, 100-pe_pct)], labels=['Profit Efficiency',''], hole=0.75, sort=False, textinfo='none', marker=dict(colors=['#00D1FF', 'rgba(255,255,255,0.05)']), hovertemplate=f"Profit Efficiency: {pe_pct:.0f}%<extra></extra>", domain=dict(x=[0,1], y=[0,1])))
    fig.add_trace(go.Pie(values=[50*hc_w, 50*(1-hc_w), 50*lc_w, 50*(1-lc_w)], labels=['HC Wins','HC Remainder','LC Wins','LC Remainder'], hole=0.85, sort=False, textinfo='none', marker=dict(colors=[green, gray, red, gray]), rotation=90, hovertemplate="%{label}: %{value:.1f}<extra></extra>", domain=dict(x=[0,1], y=[0,1])))
    fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def plot_profit_horizon(trades_df: pd.DataFrame, max_trades: int = 20):
    if trades_df.empty:
        return go.Figure()
    cols = [c for c in ['id','rr','mfe_rr','ts_open','symbol'] if c in trades_df.columns]
    d = trades_df.sort_values('ts_open', ascending=False).head(max_trades)[cols].copy()
    d['rr'] = pd.to_numeric(d.get('rr'), errors='coerce').fillna(0.0)
    d['mfe_rr'] = pd.to_numeric(d.get('mfe_rr', d['rr'].abs()), errors='coerce').fillna(d['rr'].abs())
    d['peak_extra'] = d['mfe_rr'] - d['rr']
    x = [f"{r.symbol} #{r.id}" if 'id' in d.columns and 'symbol' in d.columns else str(i) for i, r in d.iterrows()]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=d['rr'], name='Final RR', marker_color='#4cd137'))
    fig.add_trace(go.Bar(x=x, y=d['peak_extra'], name='Peak unrealized gap', marker_color='rgba(76,209,55,0.25)'))
    fig.update_layout(barmode='stack', margin=dict(t=20,l=10,r=10,b=80), xaxis_title='Trade', yaxis_title='R-multiple', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def render_discipline_posture(trades_df: pd.DataFrame, events_today: list):
    td = _today_window(trades_df)
    today_score = compute_discipline_score(td, events_today)
    # London as a proxy for last full session
    s, e = _session_window_utc('London')
    last_session_trades = trades_df[(trades_df.get('ts_open') >= s) & (trades_df.get('ts_open') <= e)] if not trades_df.empty and 'ts_open' in trades_df.columns else trades_df.iloc[:0]
    last_score = compute_discipline_score(last_session_trades, [])
    col1, col2 = st.columns(2)
    col1.metric('Discipline (Today)', f"{today_score:.0f}%" if not math.isnan(today_score) else '—')
    col2.metric('Discipline (Last Session)', f"{last_score:.0f}%" if not math.isnan(last_score) else '—')
    if 'ts_open' in trades_df.columns and not trades_df.empty:
        t = trades_df.copy()
        t['date'] = t['ts_open'].dt.date
        daily = t.groupby('date').apply(lambda g: compute_discipline_score(g, [])).reset_index(name='score')
        st.line_chart(daily.set_index('date')['score'])

def render_session_trajectory():
    eq = fetch_equity_today()
    if not isinstance(eq, list) or not eq:
        st.info('No intraday equity data.')
        return
    df = pd.DataFrame(eq)
    if not {'ts','equity'} <= set(df.columns):
        st.info('Equity payload missing fields.')
        return
    df['ts'] = pd.to_datetime(df['ts'], errors='coerce', utc=True)
    fig = go.Figure(go.Scatter(x=df['ts'], y=df['equity'], mode='lines', line=dict(color='#9b59b6')))
    fig.update_layout(margin=dict(t=10,l=10,r=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title='Time (UTC)', yaxis_title='Equity')
    st.plotly_chart(fig, use_container_width=True)

def render_behavioral_section():
    st.subheader('🧭 Behavioral Compass')
    trades = _fetch_trades(limit=300)
    events = fetch_behavior_events()
    pat = compute_patience_index(trades)
    conv = compute_conviction_rates(trades)
    pe = compute_profit_efficiency(trades)
    disc = compute_discipline_score(_today_window(trades), events)
    compass = dict(discipline=disc, patience_score=pat.get('score'), profit_eff=pe.get('avg'), hc_win=conv.get('hc_win'), lc_win=conv.get('lc_win'))
    fig = plot_behavioral_compass(compass)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with st.expander('Why these scores?'):
        if not math.isnan(disc):
            st.markdown(f"- Discipline: {disc:.0f}% (penalized by events/low-confluence trades)")
        if not math.isnan(pat.get('score') or float('nan')):
            st.markdown(f"- Patience: {pat['score']:.0f} (Δ vs {pat['baseline_s']:.0f}s baseline = {pat['delta_pct']:+.0f}%)")
        if not math.isnan(pe.get('avg') or float('nan')):
            st.markdown(f"- Profit Efficiency: {100*pe['avg']:.0f}% (avg realized/peak RR)")
    st.markdown('### 🌅 Profit Horizon')
    st.plotly_chart(plot_profit_horizon(trades), use_container_width=True, config={"displayModeBar": False})
    st.markdown('### 🧱 Discipline Posture')
    render_discipline_posture(trades, events)
    st.markdown('### 📈 Session Trajectory')
    render_session_trajectory()

with st.container():
    render_behavioral_section()
