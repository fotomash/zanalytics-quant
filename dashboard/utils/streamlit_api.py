import os
import json
import time
import threading
import queue
from typing import Any, Dict, List, Tuple

import requests
import streamlit as st


def get_api_base() -> str:
    """Resolve Django API base at runtime from session override or env."""
    base = st.session_state.get("adv19_api_base") or os.getenv("DJANGO_API_URL", "http://django:8000")
    return str(base).rstrip("/")


def api_url(path: str) -> str:
    p = (path or "").lstrip("/")
    base = get_api_base()
    if p.startswith("api/"):
        return f"{base}/{p}"
    if p.startswith(("pulse/", "risk/", "score/", "signals/")):
        parts = p.split("/", 1)
        if parts and parts[0] == "pulse" and len(parts) > 1:
            p = parts[1]
        return f"{base}/api/pulse/{p}"
    return f"{base}/{p}"


def safe_api_call(method: str, path: str, payload: Dict | None = None, timeout: float = 1.2) -> Dict:
    try:
        url = api_url(path)
        if method.upper() == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=payload or {}, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}", "url": url}
    except requests.exceptions.Timeout:
        return {"error": "API timeout", "url": api_url(path)}
    except requests.exceptions.ConnectionError:
        return {"error": "API connection failed", "url": api_url(path)}
    except Exception as e:
        return {"error": str(e), "url": api_url(path)}


@st.cache_data(show_spinner=False)
def get_trading_menu_options(yaml_path: str = "trading_menu_v2.yaml") -> List[str]:
    try:
        import yaml  # lazy import for speed
        with open(yaml_path, "r") as f:
            menu = yaml.safe_load(f) or {}
        opts: List[str] = []
        for cat in menu.get("main_categories", []) or []:
            display = cat.get("display_name", "Unknown")
            if isinstance(cat.get("subsections"), list):
                for sub in cat["subsections"]:
                    opts.append(f"{display}: {str(sub).replace('_',' ').title()}")
            elif isinstance(cat.get("components"), list):
                for comp in cat["components"]:
                    opts.append(f"{display}: {str(comp).replace('_',' ').title()}")
            elif isinstance(cat.get("features"), list):
                for feat in cat["features"]:
                    opts.append(f"{display}: {str(feat).replace('_',' ').title()}")
            else:
                opts.append(display)
        return opts or _fallback_menu()
    except Exception:
        return _fallback_menu()


def _fallback_menu() -> List[str]:
    return [
        "Strategy Selector: Real-Time Recommendation",
        "Strategy Selector: Market Regime Detection",
        "Strategy Selector: Performance Prediction",
        "Market Intelligence: Liquidity Heatmap",
        "Market Intelligence: Time Zone Analysis",
        "Market Intelligence: Session Overlap Detector",
        "Signal Command Center: Active Signals",
        "Signal Command Center: Pending Setups",
        "Signal Command Center: Risk Calculator",
        "Position Manager: Conflict Detection",
        "Position Manager: Auto-Risk Adjustment",
        "Position Manager: Performance Tracking",
    ]


def fetch_whispers() -> List[Dict[str, Any]]:
    data = safe_api_call("GET", "api/pulse/whispers") or {}
    arr = data.get("whispers") if isinstance(data, dict) else []
    return arr if isinstance(arr, list) else []


def post_whisper_ack(whisper_id: str, reason: str | None = None) -> Dict:
    return safe_api_call("POST", "api/pulse/whisper/ack", {"id": whisper_id, "reason": reason})


def post_whisper_act(whisper_id: str, action: str, details: str | None = None) -> Dict:
    payload: Dict[str, Any] = {"id": whisper_id, "action": action}
    if details:
        payload["details"] = details
    return safe_api_call("POST", "api/pulse/whisper/act", payload)


def live_status() -> Dict[str, bool]:
    out = {"market": False, "mirror": False, "equity": False}
    try:
        r = requests.get(api_url("api/v1/market/mini"), timeout=1.0)
        out["market"] = bool(r.ok)
    except Exception:
        out["market"] = False
    try:
        r = requests.get(api_url("api/v1/mirror/state"), timeout=1.0)
        out["mirror"] = bool(r.ok)
    except Exception:
        out["mirror"] = False
    try:
        r = requests.get(api_url("api/v1/feed/equity/series"), timeout=1.0)
        out["equity"] = bool(r.ok and isinstance(r.json(), dict))
    except Exception:
        out["equity"] = False
    return out


def render_status_row() -> None:
    st.caption("Live Data Status")
    status = live_status()
    cols = st.columns(3)
    for (key, label), col in zip(
        [("market", "Market"), ("mirror", "Mirror"), ("equity", "Equity")], cols
    ):
        ok = status.get(key, False)
        col.markdown(f"{'✅' if ok else '⚠️'} {label}")


def fetch_trade_history(symbol: str | None = None) -> List[Dict[str, Any]]:
    return fetch_trade_history_filtered(symbol=symbol)


def fetch_trade_history_filtered(
    *,
    symbol: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    pnl_min: float | None = None,
    pnl_max: float | None = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if symbol:
        params['symbol'] = symbol
    if date_from:
        params['date_from'] = date_from
    if date_to:
        params['date_to'] = date_to
    if pnl_min is not None:
        params['pnl_min'] = pnl_min
    if pnl_max is not None:
        params['pnl_max'] = pnl_max
    try:
        url = api_url('api/v1/trades/history')
        r = requests.get(url, params=params, timeout=3.0)
        if r.ok:
            data = r.json() or []
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def inject_glass_css() -> None:
    """Inject subtle gradient + glass card utility for a React‑like feel.

    Usage: call once near the top of the page.
    """
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(1200px 600px at 10% 10%, rgba(29,78,216,0.08) 0%, rgba(15,23,42,0.0) 60%),
                        radial-gradient(800px 400px at 90% 0%, rgba(6,182,212,0.08) 0%, rgba(15,23,42,0.0) 60%),
                        linear-gradient(135deg, #0B1220 0%, #111827 100%);
        }
        .glass { 
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px; 
            padding: 10px 14px; 
        }
        .section-title { color: #9CA3AF; font-size: 0.9rem; margin-bottom: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=30)
def fetch_symbols() -> List[str]:
    try:
        r = requests.get(api_url('api/v1/market/symbols'), timeout=2.0)
        if r.ok:
            data = r.json() or {}
            syms = data.get('symbols') if isinstance(data, dict) else []
            if isinstance(syms, list):
                return syms
    except Exception:
        pass
    return []


def render_analytics_filters(*, key_prefix: str = "flt") -> Tuple[str | None, str | None, str | None, str]:
    """Render standard Symbol and Date filters and return values:
    (symbol_or_None, date_from_iso_or_None, date_to_iso_or_None, querystring)

    key_prefix: unique prefix per page to avoid widget key collisions.
    """
    cols = st.columns(3)
    with cols[0]:
        try:
            syms = fetch_symbols() or []
        except Exception:
            syms = []
        opts = ['All'] + syms
        sel = st.selectbox("Symbol", opts, index=0, key=f"{key_prefix}_sym")
        symbol = None if sel == 'All' else sel
    with cols[1]:
        dfrom = st.date_input("From", value=None, key=f"{key_prefix}_from")
    with cols[2]:
        dto = st.date_input("To", value=None, key=f"{key_prefix}_to")

    df_str = dfrom.isoformat() if dfrom else None
    dt_str = dto.isoformat() if dto else None
    params: List[str] = []
    if symbol:
        params.append(f"symbol={symbol}")
    if df_str:
        params.append(f"date_from={df_str}")
    if dt_str:
        params.append(f"date_to={dt_str}")
    qs = ("?" + "&".join(params)) if params else ""
    return symbol, df_str, dt_str, qs


# --- SSE (Server-Sent Events) support for real-time whispers -----------

def _ensure_sse_state() -> None:
    if 'sse_whisper_queue' not in st.session_state:
        st.session_state['sse_whisper_queue'] = queue.Queue()
    if 'sse_status' not in st.session_state:
        st.session_state['sse_status'] = 'idle'
    # thread handle optional, we only track started flag
    if 'sse_thread_started' not in st.session_state:
        st.session_state['sse_thread_started'] = False


def _sse_loop() -> None:
    q: queue.Queue = st.session_state['sse_whisper_queue']
    while True:
        url = api_url('api/v1/feeds/stream?topics=whispers')
        try:
            with requests.get(url, stream=True, timeout=30) as resp:
                if resp.status_code != 200:
                    st.session_state['sse_status'] = f"error HTTP {resp.status_code}"
                    time.sleep(3)
                    continue
                st.session_state['sse_status'] = 'connected'
                current_event = None
                for raw in resp.iter_lines():
                    if raw is None:
                        continue
                    if not raw:
                        # blank line separates events
                        current_event = None
                        continue
                    line = raw.decode('utf-8', 'ignore')
                    if line.startswith('event:'):
                        current_event = line.split(':', 1)[1].strip()
                    elif line.startswith('data:'):
                        data_str = line.split(':', 1)[1].strip()
                        # only queue whisper events
                        if current_event == 'whisper':
                            try:
                                obj = json.loads(data_str) if data_str else {}
                                if obj:
                                    q.put(obj)
                            except Exception:
                                continue
        except Exception:
            st.session_state['sse_status'] = 'disconnected'
            time.sleep(3)


def start_whisper_sse() -> None:
    """Start SSE listener thread if not already running."""
    _ensure_sse_state()
    if not st.session_state['sse_thread_started']:
        st.session_state['sse_thread_started'] = True
        t = threading.Thread(target=_sse_loop, daemon=True)
        t.start()


def drain_whisper_sse(max_items: int = 50) -> List[Dict[str, Any]]:
    """Drain queued whispers from SSE into a list of items."""
    _ensure_sse_state()
    q: queue.Queue = st.session_state['sse_whisper_queue']
    out: List[Dict[str, Any]] = []
    try:
        while not q.empty() and len(out) < max_items:
            out.append(q.get_nowait())
    except Exception:
        pass
    return out


def get_sse_status() -> str:
    _ensure_sse_state()
    return str(st.session_state.get('sse_status') or 'idle')
