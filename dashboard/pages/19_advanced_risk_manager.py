"""
Zanalytics Pulse — Advanced Risk Manager
Live risk, behavior, and recent trades.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import redis
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv
# Use the dashboard-local components module to avoid path issues in Streamlit
from dashboard.components.ui_concentric import concentric_ring
from dashboard.components.ui_concentric import donut_system_overview, donut_session_vitals
from dashboard.components.ui_tri_vitals import make_three_vitals
from dashboard.components.behavioral_compass import make_behavioral_compass
from dashboard.pages.components.profit_horizon_panel import render_profit_horizon
from dashboard.pages.components.whisper_panel import render_whisper_panel
from dashboard.pages.components.whisper_timeline import render_whisper_timeline
from dashboard.pages.components.discipline_posture_panel import render_discipline_posture_panel
from dashboard.pages.components.market_header import render_market_header
from datetime import timedelta as _td
from dashboard.components.behavioral_mirror import make_behavioral_mirror
from dashboard.pages.components.whisper_panel import render_whisper_panel
from dashboard.pages.components.profit_horizon_panel import render_profit_horizon

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Load environment variables
load_dotenv()

# Baseline equity override (keeps mock aligned with production baseline)
try:
    ADV_BASELINE_EQUITY = float(
        os.getenv("MT5_BASELINE_EQUITY", "")
        or os.getenv("PULSE_BASELINE_EQUITY", "")
        or "200000"
    )
except Exception:
    ADV_BASELINE_EQUITY = 200000.0
ADV_BASELINE_CCY = os.getenv("MT5_BASELINE_CCY", "USD")

# Page configuration
st.set_page_config(
    page_title="🎯 Zanalytics Pulse — Advanced Risk Manager",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)
# --- IMAGE BACKGROUND & STYLING (match Home/Macro pages) ---
import base64

@st.cache_data(ttl=3600)
def _get_image_as_base64(path: str):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

_img_base64 = _get_image_as_base64("image_af247b.jpg")
if _img_base64:
    _background_style = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background-image: linear-gradient(rgba(0,0,0,0.80), rgba(0,0,0,0.80)), url(data:image/jpeg;base64,{_img_base64});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .main .block-container {{
        background-color: rgba(0,0,0,0.025) !important;
    }}
    </style>
    """
    st.markdown(_background_style, unsafe_allow_html=True)

# Market Conditions header
render_market_header()
# Custom CSS for enhanced styling
st.markdown("""
<style>
    :root {
        --tile-text: #ffffff;
        --tile-shadow: rgba(0,0,0,0.25);

        /* Confluence palette (latest decisions) */
        --conf-high-1: #12C48B;   /* High (>=70) — Emerald */
        --conf-high-2: #0AA66E;

        --conf-med-1: #F59E0B;    /* Medium (50-69) — Amber */
        --conf-med-2: #D97706;

        --conf-low-1: #EF4444;    /* Low (<50) — Red */
        --conf-low-2: #B91C1C;

        /* Bias palette */
        --bias-bull-1: #10B981;
        --bias-bull-2: #059669;

        --bias-neutral-1: #F59E0B;
        --bias-neutral-2: #D97706;

        --bias-bear-1: #EF4444;
        --bias-bear-2: #B91C1C;

        /* Neutral tile */
        --tile-neutral-1: #4B5563;
        --tile-neutral-2: #374151;
    }

    /* --- General cards --- */
    .risk-metric {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-high { background-color: #ffebee; color: #c62828; }
    .risk-medium { background-color: #fff3e0; color: #ef6c00; }
    .risk-low { background-color: #e8f5e9; color: #2e7d32; }

    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* --- Pulse tiles --- */
    .pulse-tile {
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        margin: 0.5rem 0;
        color: var(--tile-text);
        box-shadow: 0 8px 20px var(--tile-shadow); opacity: 0.92;
        border: 1px solid rgba(255,255,255,0.06);
        backdrop-filter: blur(4px);
    }
    .pulse-tile h4 { margin: 0 0 0.5rem 0; opacity: 0.95; }
    .pulse-tile h2 { margin: 0.25rem 0 0.5rem 0; font-weight: 800; }

    .tile-high   { background: linear-gradient(135deg, var(--conf-high-1),   var(--conf-high-2)); }
    .tile-med    { background: linear-gradient(135deg, var(--conf-med-1),    var(--conf-med-2)); }
    .tile-low    { background: linear-gradient(135deg, var(--conf-low-1),    var(--conf-low-2)); }

    .tile-bull   { background: linear-gradient(135deg, var(--bias-bull-1),   var(--bias-bull-2)); }
    .tile-neutral{ background: linear-gradient(135deg, var(--bias-neutral-1),var(--bias-neutral-2)); }
    .tile-bear   { background: linear-gradient(135deg, var(--bias-bear-1),   var(--bias-bear-2)); }

    .tile-plain  { background: linear-gradient(135deg, var(--tile-neutral-1),var(--tile-neutral-2)); }

    .tile-high, .tile-med, .tile-low, .tile-bull, .tile-neutral, .tile-bear, .tile-plain {
        filter: saturate(0.9) brightness(0.95);
        opacity: 0.92;
    }

    .risk-slider-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .psychology-insight {
        background: rgba(255,255,255,0.05);
        border-left: 3px solid rgba(153,255,208,0.85); /* neon mint accent */
        padding: 0.9rem 1rem;
        margin: 0.75rem 0;
        border-radius: 0 10px 10px 0;
        color: #eaeaea;
        box-shadow: 0 6px 18px rgba(0,0,0,0.25);
        backdrop-filter: blur(3px);
    }
    /* Make expanders (e.g., Trading in the Zone) translucent like prior UI */
    div[data-testid="stExpander"] > details {
        background: rgba(26, 29, 58, 0.35) !important;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    }
    div[data-testid="stExpander"] summary {
        color: #eaeaea !important;
    }
</style>
""", unsafe_allow_html=True)
def _confluence_band(score: float) -> str:
    """Return 'high' for &gt;=70, 'med' for 50-69, 'low' for &lt;50."""
    try:
        s = float(score)
    except Exception:
        return "med"
    if s >= 70:
        return "high"
    if s >= 50:
        return "med"
    return "low"

def _bias_class(score: float) -> str:
    """Map score to bull/neutral/bear class for tile coloring."""
    try:
        s = float(score)
    except Exception:
        return "neutral"
    if s > 60:
        return "bull"
    if s < 40:
        return "bear"
    return "neutral"

# API Configuration (runtime-resolved to honor in‑app override)
def _pulse_url(path: str) -> str:
    """Normalize paths to pulse endpoints under /api/pulse/"""
    try:
        base = (st.session_state.get('adv19_api_base') or os.getenv("DJANGO_API_URL", "http://django:8000")).rstrip('/')
    except Exception:
        base = (os.getenv("DJANGO_API_URL", "http://django:8000") or "http://django:8000").rstrip('/')
    p = path.lstrip('/')
    if p.startswith('api/'):
        return f"{base}/{p}"
    # Common pulse endpoints used on this page
    if p.startswith(('pulse/', 'risk/', 'score/', 'signals/')):
        # strip optional leading 'pulse/' then prefix with api/pulse
        p2 = p.split('/', 1)
        if p2 and p2[0] == 'pulse' and len(p2) > 1:
            p = p2[1]
        return f"{base}/api/pulse/{p}"
    return f"{base}/{p}"

def safe_api_call(method: str, path: str, payload: Dict = None, timeout: float = 1.2) -> Dict:
    """Safe API call with error handling and fallbacks"""
    try:
        url = _pulse_url(path)
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload or {}, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        if response.status_code == 200:
            return response.json()
        return {"error": f"HTTP {response.status_code}", "url": url}
    except requests.exceptions.Timeout:
        return {"error": "API timeout", "url": _pulse_url(path)}
    except requests.exceptions.ConnectionError:
        return {"error": "API connection failed", "url": _pulse_url(path)}
    except Exception as e:
        return {"error": str(e), "url": _pulse_url(path)}


def render_api_health_card(pulse_manager: "AdvancedPulseRiskManager") -> None:
    """Render a compact API Health card for Pulse and MT5 bridge."""
    # Pulse API health
    pulse_health = safe_api_call("GET", "pulse/health")
    pulse_ok = isinstance(pulse_health, dict) and "error" not in pulse_health
    pulse_status = pulse_health.get("status", "unknown") if isinstance(pulse_health, dict) else "unknown"
    pulse_lag = pulse_health.get("lag_ms") if isinstance(pulse_health, dict) else None

    # MT5 bridge health
    mt5_base = getattr(pulse_manager, "mt5_url", None)
    mt5_ok = False
    mt5_detail = ""
    if mt5_base:
        try:
            url = f"{str(mt5_base).rstrip('/')}/account_info"
            r = requests.get(url, timeout=2.5)
            if r.ok:
                data = r.json() or {}
                # consider either dict or list payloads
                if isinstance(data, list) and data:
                    data = data[0]
                mt5_ok = isinstance(data, dict) and bool(data)
                login = data.get("login") or data.get("Login") or "—"
                server = data.get("server") or data.get("Server") or ""
                mt5_detail = f"{login} {server}" if login != "—" else "OK"
            else:
                mt5_detail = f"HTTP {r.status_code}"
        except Exception as e:
            mt5_detail = f"error: {e}"
    else:
        mt5_detail = "no URL"

    # Render card
    st.markdown("### 🔧 API Health")
    c1, c2, c3 = st.columns([1.2, 1.2, 2])
    with c1:
        st.metric(
            "Pulse API",
            "UP" if pulse_ok else "DOWN",
            f"{pulse_status} | lag {pulse_lag}ms" if pulse_ok and pulse_lag is not None else pulse_status,
        )
    with c2:
        st.metric(
            "MT5 Bridge",
            "UP" if mt5_ok else "DOWN",
            mt5_detail,
        )
    with c3:
        # Show last status messages for quick diagnostics
        msgs = getattr(pulse_manager, "status_messages", [])
        if msgs:
            st.caption("; ".join(msgs[-3:]))

class AdvancedPulseRiskManager:
    """Advanced Risk Manager with behavioral insights"""

    def __init__(self):
        # Get credentials from environment (no defaults to real values)
        self.mt5_login = os.getenv('MT5_LOGIN')
        self.mt5_password = os.getenv('MT5_PASSWORD')
        self.mt5_server = os.getenv('MT5_SERVER')
        
        # Initialize connections
        self.connected = False
        self.mt5_available = MT5_AVAILABLE
        self._last_account_info: Dict = {}
        # Optional HTTP MT5 bridge (align with page 16) with robust fallbacks
        # Allow UI/session override to be first candidate
        ui_override = st.session_state.get('adv19_bridge_url')
        self._mt5_candidates = [
            ui_override,
            os.getenv("MT5_URL"),
            os.getenv("MT5_API_URL"),
            os.getenv("MT5_PUBLIC_URL"),
            "http://mt5:5001",
            "http://localhost:5001",
            "http://127.0.0.1:5001",
        ]
        self.mt5_url = next((u for u in self._mt5_candidates if u), None)
        self.bridge_available = False
        self.status_messages: List[str] = []
        
        # Redis connection with error handling
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'), 
                port=int(os.getenv('REDIS_PORT', 6379)), 
                decode_responses=True,
                socket_timeout=2.0
            )
            self.redis_client.ping()
            self.redis_available = True
        except Exception:
            self.redis_available = False
            self.redis_client = None

    def connect(self) -> bool:
        """Connect to MT5 with proper error handling (quiet if unavailable)."""
        if not self.mt5_available:
            return False
        if not all([self.mt5_login, self.mt5_password, self.mt5_server]):
            return False

        try:
            if not mt5.initialize():
                return False

            authorized = mt5.login(
                login=int(self.mt5_login),
                password=self.mt5_password,
                server=self.mt5_server
            )

            if authorized:
                self.connected = True
                return True
            return False
        except Exception as e:
            st.error(f"MT5 Connection Error: {e}")
            return False

    # --- Simple cache (Redis preferred, fallback to session) ---
    def _cache_get(self, key: str):
        try:
            if getattr(self, 'redis_available', False) and self.redis_client:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
        except Exception:
            pass
        try:
            skey = f"cache:{key}"
            row = st.session_state.get(skey)
            if isinstance(row, dict) and row.get('exp', 0) > time.time():
                return row.get('data')
        except Exception:
            pass
        return None

    def _cache_set(self, key: str, data, ttl_seconds: int = 5):
        try:
            if getattr(self, 'redis_available', False) and self.redis_client:
                self.redis_client.set(key, json.dumps(data), ex=ttl_seconds)
                return
        except Exception:
            pass
        try:
            skey = f"cache:{key}"
            st.session_state[skey] = {'data': data, 'exp': time.time() + ttl_seconds}
        except Exception:
            pass

    def get_account_info(self) -> Dict:
        """Get account information. No mocks; only real sources (match page 16)."""
        ck = "adv19:account_info"
        cached = self._cache_get(ck)
        if isinstance(cached, dict) and cached:
            return cached
        def _normalize(ai: Dict) -> Dict:
            """Normalize various bridge shapes: lower-case keys, handle nested/list, coerce numbers."""
            obj = ai
            if isinstance(obj, list) and obj:
                obj = obj[0]
            if not isinstance(obj, dict):
                return {}
            norm = {str(k).lower(): v for k, v in obj.items()}
            # Coerce common numeric fields to floats when possible
            for k in [
                'balance','equity','margin','free_margin','margin_level','profit','leverage'
            ]:
                if k in norm and norm[k] is not None:
                    try:
                        norm[k] = float(norm[k])
                    except Exception:
                        pass
            # Keep original login/server/company if present
            return norm
        # Try HTTP MT5 bridge first; skip stub/placeholder responses
        # Try bridge endpoints across candidates until success
        tried = []
        for base in [u for u in self._mt5_candidates if u]:
            try:
                url = f"{str(base).rstrip('/')}/account_info"
                tried.append(url)
                r = requests.get(url, timeout=0.9)
                if r.ok:
                    raw = r.json() or {}
                    # Skip obvious stub/placeholder
                    if isinstance(raw, dict) and (str(raw.get('login','')).lower() == 'placeholder' or raw.get('source') == 'stub'):
                        self.status_messages.append(f"Skipped stub from {url}")
                        continue
                    data = _normalize(raw)
                    if isinstance(data, dict) and data and 'equity' in data:
                        self.bridge_available = True
                        self.mt5_url = base  # lock onto the working base
                        self._cache_set(ck, data, ttl_seconds=5)
                        return data
                else:
                    self.status_messages.append(f"HTTP bridge {url} returned {r.status_code}")
            except Exception as e:
                self.status_messages.append(f"HTTP bridge error @ {base}: {e}")
        if tried:
            self.status_messages.append(f"Tried: {', '.join(tried)}")
        # Try native MT5 if available and credentials are set
        if self.mt5_available and all([self.mt5_login, self.mt5_password, self.mt5_server]):
            try:
                if not self.connected:
                    if mt5.initialize() and mt5.login(login=int(self.mt5_login), password=self.mt5_password, server=self.mt5_server):
                        self.connected = True
                if self.connected:
                    ai = mt5.account_info()
                    if ai:
                        info = {
                            'login': ai.login,
                            'server': ai.server,
                            'balance': ai.balance,
                            'equity': ai.equity,
                            'margin': ai.margin,
                            'free_margin': ai.margin_free,
                            'margin_level': ai.margin_level,
                            'profit': ai.profit,
                            'leverage': ai.leverage,
                            'currency': ai.currency,
                            'name': ai.name,
                            'company': ai.company,
                        }
                        self._cache_set(ck, info, ttl_seconds=5)
                        return info
            except Exception as e:
                self.status_messages.append(f"MT5 native error: {e}")
        # No data available
        return {}

    def get_positions(self) -> pd.DataFrame:
        """Get all open positions with error handling (match page 16)."""
        ck = "adv19:positions"
        cached = self._cache_get(ck)
        if isinstance(cached, list):
            try:
                return pd.DataFrame(cached)
            except Exception:
                pass
        # Try HTTP MT5 bridge if available
        try:
            if self.mt5_url:
                r = requests.get(f"{str(self.mt5_url).rstrip('/')}/positions_get", timeout=0.9)
                if r.ok:
                    self.bridge_available = True
                    data = r.json() or []
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                        # Normalize time columns if present (seconds/ms/ns or ISO strings)
                        try:
                            if 'time_msc' in df.columns:
                                df['time'] = pd.to_datetime(pd.to_numeric(df['time_msc'], errors='coerce'), unit='ms', errors='coerce')
                            for col in ("time", "time_update"):
                                if col not in df.columns:
                                    continue
                                s = df[col]
                                nums = pd.to_numeric(s, errors='coerce')
                                if nums.notna().any():
                                    v = float(nums.dropna().iloc[0])
                                    unit = 's'
                                    if v > 1e18:
                                        unit = 'ns'
                                    elif v > 1e12:
                                        unit = 'ms'
                                    df[col] = pd.to_datetime(nums, unit=unit, errors='coerce')
                                else:
                                    df[col] = pd.to_datetime(s, errors='coerce')
                        except Exception:
                            pass
                        try:
                            self._cache_set(ck, df.to_dict(orient='records'), ttl_seconds=5)
                        except Exception:
                            pass
                        return df
        except Exception:
            pass
        # Try native MT5 if connected/available
        try:
            if self.mt5_available:
                if not self.connected and self.mt5_login and self.mt5_password and self.mt5_server:
                    if mt5.initialize() and mt5.login(login=int(self.mt5_login), password=self.mt5_password, server=self.mt5_server):
                        self.connected = True
                if self.connected:
                    positions = mt5.positions_get()
                    if positions is None or len(positions) == 0:
                        return pd.DataFrame()
                    df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
                    try:
                        if 'time_msc' in df.columns:
                            df['time'] = pd.to_datetime(pd.to_numeric(df['time_msc'], errors='coerce'), unit='ms', errors='coerce')
                        for col in ("time", "time_update"):
                            if col in df.columns:
                                nums = pd.to_numeric(df[col], errors='coerce')
                                v = float(nums.dropna().iloc[0]) if nums.notna().any() else None
                                unit = 's'
                                if v is not None and v > 1e18:
                                    unit = 'ns'
                                elif v is not None and v > 1e12:
                                    unit = 'ms'
                                df[col] = pd.to_datetime(nums if nums.notna().any() else df[col], unit=unit if nums.notna().any() else None, errors='coerce')
                    except Exception:
                        pass
                    try:
                        self._cache_set(ck, df.to_dict(orient='records'), ttl_seconds=5)
                    except Exception:
                        pass
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    def get_confluence_score(self) -> Dict:
        """Get confluence score from Pulse API (short timeout, tolerate errors)."""
        ck = "adv19:confluence"
        cached = self._cache_get(ck)
        if isinstance(cached, dict) and cached:
            return cached
        result = safe_api_call("POST", "score/peek", {}, timeout=0.9)
        if isinstance(result, dict) and 'error' not in result:
            self._cache_set(ck, result, ttl_seconds=5)
            return result
        return {}

    def get_risk_summary(self) -> Dict:
        """Get risk summary: Redis latest → API (short timeout) → empty."""
        ck = "adv19:risk_summary"
        cached = self._cache_get(ck)
        if isinstance(cached, dict) and cached:
            return cached
        # Try Redis key
        try:
            if getattr(self, 'redis_available', False) and self.redis_client:
                raw = self.redis_client.get('pulse:risk:latest')
                if raw:
                    data = json.loads(raw)
                    self._cache_set(ck, data, ttl_seconds=5)
                    return data
        except Exception:
            pass
        # API
        result = safe_api_call("GET", "risk/summary", timeout=1.0)
        if isinstance(result, dict) and 'error' not in result:
            self._cache_set(ck, result, ttl_seconds=5)
            return result
        return {}

    def get_dashboard_data(self) -> Dict:
        """Fetch consolidated dashboard data from Django API if available.
        Expected shape: { account_info, risk_management, open_positions, psychological_state, confluence }
        """
        data = safe_api_call("GET", "api/v1/dashboard-data/")
        if isinstance(data, dict) and 'error' not in data:
            return data
        # Fallbacks
        data = safe_api_call("GET", "dashboard-data/")
        return data if isinstance(data, dict) and 'error' not in data else {}

    def get_top_opportunities(self, n: int = 3) -> List[Dict]:
        """Get top trading opportunities. No mocks."""
        result = safe_api_call("GET", f"signals/top?n={n}")
        return result if isinstance(result, list) else []

    def get_recent_trades(self, limit: int = 10, days: int = 7) -> pd.DataFrame:
        """Fetch recent trades from MT5 bridge; return empty DF on failure."""
        ck = f"adv19:recent_trades:{limit}:{days}"
        cached = self._cache_get(ck)
        if isinstance(cached, list):
            try:
                return pd.DataFrame(cached)
            except Exception:
                pass
        eps = [
            f"history_deals_get?days={days}&limit={limit}",
            f"history_orders_get?days={days}&limit={limit}",
            f"history_deals_get?from={(datetime.now()-timedelta(days=days)).isoformat()}&to={datetime.now().isoformat()}&limit={limit}",
        ]
        for ep in eps[:2]:
            try:
                r = requests.get(f"{self.mt5_url}/{ep}", timeout=0.9)
                if not r.ok:
                    continue
                data = r.json() or []
                if not isinstance(data, list) or not data:
                    continue
                df = pd.DataFrame(data)
                # normalize time
                tcols = [c for c in ["time", "time_msc", "time_done", "time_close"] if c in df.columns]
                if tcols:
                    col = tcols[0]
                    try:
                        df["time"] = pd.to_datetime(df[col], unit='s', errors='coerce')
                    except Exception:
                        df["time"] = pd.to_datetime(df[col], errors='coerce')
                elif "timestamp" in df.columns:
                    df["time"] = pd.to_datetime(df["timestamp"], errors='coerce')
                if "type" in df.columns:
                    df["type"] = df["type"].replace({0: "BUY", 1: "SELL", 2: "BUY", 3: "SELL"})
                keep = [c for c in ["time","ticket","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in df.columns]
                if "time" in keep:
                    df = df.sort_values("time", ascending=False)
                out = df[keep].head(limit) if keep else df.head(limit)
                try:
                    self._cache_set(ck, out.to_dict(orient='records'), ttl_seconds=10)
                except Exception:
                    pass
                return out
            except Exception:
                continue
        return pd.DataFrame()

def create_risk_allocation_3d(account_equity: float,
                              anticipated_trades: int,
                              daily_risk_pct: float = 3.0) -> go.Figure:
    """3D-looking surface: per-trade risk ($) vs anticipated trades (fixed 3% daily budget).

    X: anticipated trades (1..12)
    Y: dummy 0..1 band for 3D effect (no labeling)
    Z: per-trade risk dollars = equity * 3% / X
    """
    daily_risk_amount = max(0.0, float(account_equity) * (float(daily_risk_pct) / 100.0))
    x_vals = np.arange(1, 13)
    y_vals = np.linspace(0.0, 1.0, 5)
    X, Y = np.meshgrid(x_vals, y_vals)
    Z_line = np.where(x_vals > 0, daily_risk_amount / x_vals, 0.0)
    Z = np.tile(Z_line, (len(y_vals), 1))

    fig = go.Figure(data=[go.Surface(
        x=X, y=Y, z=Z,
        colorscale='Turbo',
        showscale=False,  # hide vertical color bar
        contours={"z": {"show": False}},  # remove horizontal contour lines
        lighting=dict(ambient=0.45, diffuse=0.6, roughness=0.65, specular=0.2),
        hovertemplate='Trades %{x}<br>Conf %{y:.0f}%<br>$%{z:,.0f}<extra></extra>',
        opacity=0.92,
        name='Allocation Surface'
    )])

    # Current selection marker
    x0 = max(1, int(anticipated_trades))
    y0 = 0.5
    z0 = (daily_risk_amount / x0)
    fig.add_trace(go.Scatter3d(
        x=[x0], y=[y0], z=[z0],
        mode='markers+text',
        text=[f"${z0:,.0f}"],
        textposition='top center',
        marker=dict(size=6, color='#FFB703', symbol='diamond'),
        hovertemplate='Current • Trades %{x}, Conf %{y:.0f}%<br>$%{z:,.0f}<extra></extra>',
        name='Current'
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title='Anticipated Trades',
            yaxis_title='',
            zaxis_title='Per-Trade Risk ($)',
            xaxis=dict(
                backgroundcolor='rgba(0,0,0,0.0)', gridcolor='rgba(255,255,255,0.12)',
                tickmode='linear', dtick=1
            ),
            yaxis=dict(
                backgroundcolor='rgba(0,0,0,0.0)', gridcolor='rgba(255,255,255,0.12)',
                tickmode='array', tickvals=[]
            ),
            zaxis=dict(
                backgroundcolor='rgba(0,0,0,0.0)', gridcolor='rgba(255,255,255,0.12)',
                tickformat=',.0f'
            ),
            camera=dict(eye=dict(x=1.6, y=1.6, z=0.8)),
            aspectmode='manual', aspectratio=dict(x=1.2, y=1.0, z=0.6)
        ),
        title=dict(text=f'Risk Allocation 3D ({daily_risk_pct:.1f}% daily)', x=0.01, xanchor='left', y=0.95),
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_psychology_insights(confluence_score: float, 
                              consecutive_losses: int, 
                              trades_today: int,
                              risk_phase: str) -> List[str]:
    """Generate behavioral psychology insights"""
    
    insights = []
    
    # Confidence-based insights
    if confluence_score > 85:
        insights.append("🟢 High confidence signal - maintain discipline but avoid overconfidence")
    elif confluence_score < 40:
        insights.append("🔴 Low confidence signal - consider skipping or reducing position size")
    
    # Loss-based insights
    if consecutive_losses >= 2:
        insights.append("⚠️ Multiple consecutive losses - activate cooling off period")
    
    # Trade frequency insights
    if trades_today >= 4:
        insights.append("⚠️ High trade frequency today - watch for fatigue effects")
    
    # Risk phase insights
    phase_insights = {
        "low_equity": "🟡 Conservative phase - focus on high probability setups",
        "stable": "🟢 Stable phase - normal risk parameters apply",
        "new_high": "🟢 Growth phase - can increase position size slightly",
        "recovery": "🟡 Recovery phase - reduce risk until back to stable"
    }
    insights.append(phase_insights.get(risk_phase, "Unknown phase"))
    
    return insights

def render_risk_control_panel(account_info: Dict, risk_summary: Dict):
    """Render risk controls in the sidebar and persist selections."""
    with st.sidebar.expander("🎛️ Risk Controls", expanded=True):
        st.markdown("#### Risk Parameters")
        # Daily risk percent slider (bring back 0.2% → 3%)
        daily_risk_pct = st.slider(
            "Daily Risk %",
            min_value=0.2, max_value=3.0, step=0.1, value=3.0,
            help="Percent of equity you're willing to risk today"
        )
        daily_profit_pct = st.slider(
            "Daily Profit Target %",
            min_value=0.2, max_value=5.0, step=0.1, value=1.0,
            help="Target gain for the day; walk away once reached"
        )
        # Anticipated trades slider
        anticipated_trades = st.slider(
            "Anticipated Trades Today",
            1, 12, 5,
            help="Number of trades you plan to take today"
        )
        # Compute per-trade dollars
        equity = float(account_info.get('equity') or 0)
        daily_risk_amount = equity * (daily_risk_pct / 100.0)
        per_trade_dollars = daily_risk_amount / anticipated_trades if anticipated_trades else 0.0
        st.metric(
            "Per-Trade Risk ($)",
            f"${per_trade_dollars:,.0f}",
            f"{daily_risk_pct:.1f}% daily: ${daily_risk_amount:,.0f}"
        )
        # Small fine-tune slider under per-trade risk
        fine_tune = st.slider(
            "Fine-tune Per-Trade (x)",
            min_value=0.5, max_value=1.5, step=0.05, value=1.0,
            help="Quickly nudge per-trade risk up/down"
        )
        per_trade_dollars *= fine_tune
        st.caption(f"Adjusted per-trade: ${per_trade_dollars:,.0f} (x{fine_tune:.2f})")

        # Persist selections for use elsewhere on the page
        st.session_state['adv19_daily_risk_pct'] = float(daily_risk_pct)
        st.session_state['adv19_daily_profit_pct'] = float(daily_profit_pct)
        st.session_state['adv19_anticipated_trades'] = int(anticipated_trades)
        st.session_state['adv19_per_trade_risk'] = float(per_trade_dollars)
        st.caption("Settings persist across tabs for this session.")


# === Whisperer: Discipline Posture, Behavioral Mirror, Session Trajectory, Target Status ===
def _compute_discipline_today(risk_summary: Dict) -> float:
    try:
        # Start at 100, subtract for risk used and warnings
        daily_used = float(risk_summary.get('daily_risk_used', 0) or 0)
        warnings = risk_summary.get('warnings', []) or []
        score = 100.0 - min(40.0, daily_used) - (len(warnings) * 8.0)
        return max(0.0, min(100.0, score))
    except Exception:
        return 100.0


def _render_discipline_posture(risk_summary: Dict):
    # Prefer backend summary if available
    try:
        dj = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
        resp = requests.get(f"{dj}/api/v1/discipline/summary", timeout=1.0)
        if resp.ok:
            ds = resp.json() or {}
            today = float(ds.get('today') or _compute_discipline_today(risk_summary))
            seven = ds.get('seven_day') or []
            events_today = ds.get('events_today') or []
        else:
            today = _compute_discipline_today(risk_summary)
            seven = []
            events_today = []
    except Exception:
        today = _compute_discipline_today(risk_summary)
        seven = []
        events_today = []
    # Maintain simple history for 7-day sparkline
    if seven:
        hist = [float(x.get('score', 0)) for x in seven][-7:]
    else:
        key = 'adv19_discipline_7d'
        hist = st.session_state.get(key) or []
        if not hist:
            hist = [max(50.0, today - 10)] * 6 + [today]
        else:
            if len(hist) >= 7:
                hist = hist[-6:] + [today]
            else:
                hist = hist + [today]
        st.session_state[key] = hist

    last_session = float(st.session_state.get('adv19_discipline_prev', today))
    st.session_state['adv19_discipline_prev'] = today

    colA, colB = st.columns([2, 1])
    with colA:
        # Two vertical bars: today vs last session
        fig = go.Figure()
        fig.add_trace(go.Bar(x=['Today'], y=[today], marker_color='rgba(16,185,129,0.85)'))
        fig.add_trace(go.Bar(x=['Prev'], y=[last_session], marker_color='rgba(156,163,175,0.55)'))
        fig.update_layout(height=220, yaxis=dict(range=[0, 100], title='Discipline %'), showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        # 7d sparkline
        xs = list(range(1, len(hist) + 1))
        fig_s = go.Figure(go.Scatter(x=xs, y=hist, mode='lines', line=dict(color='#22d3ee', width=2)))
        fig_s.update_layout(height=220, xaxis=dict(visible=False), yaxis=dict(visible=False, range=[0, 100]), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_s, use_container_width=True)
    # Tooltip-like details
    ws = risk_summary.get('warnings') or []
    if ws:
        st.caption('Why: ' + '; '.join(str(w) for w in ws[:3]))


def _render_behavioral_mirror(recent_df: pd.DataFrame, risk_summary: Dict):
    # Discipline Score (%): use today discipline
    disc = _compute_discipline_today(risk_summary)
    # Patience Index: avg minutes between trades today
    patience = '—'
    try:
        df = recent_df.copy()
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df.sort_values('time')
        today = pd.Timestamp.now().normalize()
        dft = df[df['time'] >= today]
        if len(dft) >= 2:
            deltas = dft['time'].diff().dropna()
            patience = f"{(deltas.mean().total_seconds()/60):.0f}m"
    except Exception:
        pass
    # Conviction Rate (%): win rate when comment or tag includes 'high' vs others
    conviction = '—'
    try:
        df = recent_df.copy()
        df['pl_total'] = df.get('profit', 0) + df.get('commission', 0) + df.get('swap', 0)
        high = df[df.get('comment', '').astype(str).str.contains('high', case=False, na=False)]
        low = df[~df.index.isin(high.index)]
        def wr(d):
            return (d['pl_total'] > 0).mean() * 100 if len(d) else 0
        conviction = f"{wr(high):.0f}% vs {wr(low):.0f}%"
    except Exception:
        pass
    # Profit Efficiency (%): captured vs max excursion (requires price path; approximate using profit vs 1.5R cap)
    efficiency = '—'
    try:
        df = recent_df.copy()
        R = 1.0
        if len(df):
            eff = (df['profit'].clip(lower=0).mean()) / (R * max(1, len(df))) * 100
            efficiency = f"{eff:.0f}%"
    except Exception:
        pass
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric('Discipline', f"{disc:.0f}%")
    with m2:
        st.metric('Patience', f"{patience}")
    with m3:
        st.metric('Conviction', f"{conviction}")
    with m4:
        st.metric('Profit Efficiency', f"{efficiency}")


def _render_behavioral_concentric(recent_df: pd.DataFrame, risk_summary: Dict, title: str = "Behavioral Mirror (Concentric)"):
    """Render concentric bipolar rings: outer=Patience, middle=Discipline, inner=Profit Efficiency."""
    # Discipline (0..100) → ratio relative to baseline 70
    disc = _compute_discipline_today(risk_summary)
    disc_ratio = (disc - 70.0) / 30.0  # ~70 neutral
    disc_ratio = max(-1.0, min(1.0, disc_ratio))
    # Patience: average minutes between trades today vs target 15m
    patience_ratio = 0.0
    try:
        df = recent_df.copy()
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        dft = df[df['time'] >= pd.Timestamp.now().normalize()].sort_values('time')
        if len(dft) >= 2:
            mins = dft['time'].diff().dropna().mean().total_seconds() / 60.0
            patience_ratio = (mins - 15.0) / 15.0  # >0 is good
            patience_ratio = max(-1.0, min(1.0, patience_ratio))
    except Exception:
        patience_ratio = 0.0
    # Profit Efficiency: 0..100 → ratio centered at 50
    eff_ratio = 0.0
    try:
        df = recent_df.copy()
        if len(df):
            eff = (df['profit'].clip(lower=0).mean() if 'profit' in df.columns else 0.0)
            # Approximated vs per-trade notional; center at nominal 50%
            eff_pct = 50.0 if eff == 0 else 60.0  # placeholder if no resolution
            eff_ratio = (eff_pct - 50.0) / 50.0
            eff_ratio = max(-1.0, min(1.0, eff_ratio))
    except Exception:
        eff_ratio = 0.0

    st.markdown(f"#### {title}")
    fig = go.Figure()
    # Outer ring: Patience
    patience_color = '#22c55e' if patience_ratio >= 0 else '#ef4444'
    fig.add_trace(go.Pie(values=[abs(patience_ratio), 1-abs(patience_ratio)], hole=0.55,
                         marker=dict(colors=[patience_color, 'rgba(255,255,255,0.06)']), textinfo='none',
                         direction='clockwise' if patience_ratio>=0 else 'counterclockwise', sort=False, showlegend=False))
    # Middle ring: Discipline
    disc_color = '#22c55e' if disc_ratio >= 0 else '#ef4444'
    fig.add_trace(go.Pie(values=[abs(disc_ratio), 1-abs(disc_ratio)], hole=0.70,
                         marker=dict(colors=[disc_color, 'rgba(255,255,255,0.06)']), textinfo='none',
                         direction='clockwise' if disc_ratio>=0 else 'counterclockwise', sort=False, showlegend=False))
    # Inner ring: Profit Efficiency
    eff_color = '#22c55e' if eff_ratio >= 0 else '#ef4444'
    fig.add_trace(go.Pie(values=[abs(eff_ratio), 1-abs(eff_ratio)], hole=0.82,
                         marker=dict(colors=[eff_color, 'rgba(255,255,255,0.06)']), textinfo='none',
                         direction='clockwise' if eff_ratio>=0 else 'counterclockwise', sort=False, showlegend=False))
    fig.update_traces(rotation=270)
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Outer: Patience • Middle: Discipline • Inner: Profit Efficiency")


def _render_session_trajectory(account_info: Dict, risk_summary: Dict):
    # Prefer live intraday equity series feed; fallback to local trail
    try:
        series = safe_api_call("GET", "api/v1/feed/equity/series") or {}
    except Exception:
        series = {}
    pts = series.get('points') if isinstance(series, dict) else []
    fig = go.Figure()
    if isinstance(pts, list) and pts:
        try:
            xs = [pd.to_datetime(p.get('ts')) for p in pts]
            ys = [float(p.get('pnl') or 0.0) for p in pts]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode='lines', name='P&L', line=dict(color='#22c55e', width=2), fill='tozeroy', fillcolor='rgba(34,197,94,0.10)'))
            fig.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.3)
        except Exception:
            pass
    else:
        # Fallback: build local equity breadcrumb (not persisted)
        key = 'adv19_equity_intraday'
        L = st.session_state.get(key) or []
        now = datetime.now()
        eq = float(account_info.get('equity', 0) or 0)
        L.append({'ts': now.isoformat(), 'equity': eq})
        st.session_state[key] = L[-600:]
        xs = [pd.to_datetime(x['ts']) for x in st.session_state[key]]
        ys = [float(x['equity']) for x in st.session_state[key]]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode='lines', name='Equity', line=dict(color='#60a5fa', width=2)))
    # Overlay behavioral markers if available (best-effort from warnings)
    ws = risk_summary.get('warnings') or []
    if any('Revenge' in str(w) for w in ws):
        if xs:
            fig.add_trace(go.Scatter(x=[xs[-1]], y=[ys[-1]], mode='markers', marker=dict(color='red', size=10), name='Revenge'))
    if any('Overconfidence' in str(w) for w in ws):
        if xs:
            fig.add_trace(go.Scatter(x=[xs[-1]], y=[ys[-1]], mode='markers', marker=dict(color='yellow', size=10), name='Overconfidence'))
    # Profit milestone marker hint (last point when milestone event exists stored earlier)
    try:
        if st.session_state.get('adv19_last_milestone'):
            ts, val = st.session_state['adv19_last_milestone']
            fig.add_trace(go.Scatter(x=[pd.to_datetime(ts)], y=[float(val)], mode='markers', marker=dict(color='green', size=10), name='Milestone'))
    except Exception:
        pass
    fig.update_layout(height=260, margin=dict(l=20, r=10, t=10, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
    # Session Vitals (prototype)
    with st.expander("🫀 Session Vitals (Prototype)", expanded=False):
        try:
            eq = float(account_info.get('equity') or 0)
            bal = float(account_info.get('balance') or 0)
            # fetch risk env fresh to avoid stale cache
            risk_env = safe_api_call("GET", "api/v1/account/risk") or {}
            sod = float(risk_env.get('sod_equity') or bal or eq)
            target_amt = float(risk_env.get('target_amount') or 0)
            loss_amt = float(risk_env.get('loss_amount') or 0)
            pnl = eq - sod
            prog_target = max(0.0, min(1.0, (pnl/target_amt))) if (pnl >= 0 and target_amt > 0) else 0.0
            prog_loss = max(0.0, min(1.0, (abs(pnl)/loss_amt))) if (pnl < 0 and loss_amt > 0) else 0.0
            dd_used = max(0.0, min(1.0, ((sod - eq)/loss_amt))) if (eq < sod and loss_amt > 0) else 0.0
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Balance**")
                st.metric("Account Balance", f"${bal:,.0f}")
                st.caption("Long‑term health (baseline reference)")
            with c2:
                st.markdown("**Equity (Daily DD)**")
                st.progress(dd_used)
                st.caption(f"Daily DD used: {dd_used*100:.0f}%")
            with c3:
                st.markdown("**P&L Progress**")
                if pnl >= 0:
                    st.progress(prog_target)
                    st.caption(f"Toward target: {prog_target*100:.0f}% (P&L +${pnl:,.0f} of +${target_amt:,.0f})")
                else:
                    st.progress(prog_loss)
                    st.caption(f"Toward loss cap: {prog_loss*100:.0f}% (P&L -${abs(pnl):,.0f} of -${loss_amt:,.0f})")
        except Exception:
            st.info("Vitals unavailable")
    # Trade History (behavioral analysis)
    try:
        from dashboard.utils.streamlit_api import fetch_trade_history_filtered, fetch_symbols
        st.subheader("Trade History")
        sym_list = fetch_symbols() or []
        sym_opts = ['All'] + sym_list
        sel = st.selectbox("Filter by Symbol", sym_opts, key='hist_sym')
        sym = None if sel == 'All' else sel
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            dfrom = st.date_input("From", value=None, key='hist_from')
        with c2:
            dto = st.date_input("To", value=None, key='hist_to')
        with c3:
            pmin = st.number_input("Min PnL", value=0.0, step=10.0, format="%f", key='hist_pmin')
        with c4:
            pmax = st.number_input("Max PnL", value=0.0, step=10.0, format="%f", key='hist_pmax')
        data = fetch_trade_history_filtered(
            symbol=sym,
            date_from=(dfrom.isoformat() if dfrom else None),
            date_to=(dto.isoformat() if dto else None),
            pnl_min=(pmin if pmin != 0.0 else None),
            pnl_max=(pmax if pmax != 0.0 else None),
        )
        df = pd.DataFrame(data)
        if not df.empty:
            # Quick stats
            try:
                pnl_series = pd.to_numeric(df.get('pnl'), errors='coerce').fillna(0.0)
                total = len(df)
                wins = int((pnl_series > 0).sum())
                losses = int((pnl_series < 0).sum())
                winrate = (wins/total*100.0) if total else 0.0
                avg_pnl = float(pnl_series.mean()) if total else 0.0
                cst1, cst2, cst3 = st.columns(3)
                cst1.metric("Trades", f"{total}")
                cst2.metric("Win Rate", f"{winrate:.0f}%")
                cst3.metric("Avg PnL", f"${avg_pnl:,.2f}")
            except Exception:
                pass
            if 'ts' in df.columns:
                df['ts'] = pd.to_datetime(df['ts'], errors='coerce')
            cols = [c for c in ['id','ts','symbol','direction','entry','exit','pnl','status'] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, height=300)
            csv = df[cols].to_csv(index=False).encode('utf-8')
            st.download_button("Export to CSV", csv, "trade_history.csv", "text/csv")
        else:
            st.info("No trade history yet.")
    except Exception:
        pass


def _render_target_status(profit_val: float, equity_val: float, daily_profit_pct: float, milestone_threshold: float = 0.75):
    target_amt = equity_val * (daily_profit_pct / 100.0) if equity_val else 0.0
    prog = (max(0.0, profit_val) / target_amt) if target_amt > 0 else 0.0
    # Simple circular progress via pie donut
    fig = go.Figure(data=[
        go.Pie(values=[prog, max(0.0, 1.0 - prog)], hole=0.7, marker=dict(colors=['#22c55e', 'rgba(255,255,255,0.08)']), textinfo='none')
    ])
    label = "Protect" if prog >= milestone_threshold else f"{int(prog*100)}%"
    fig.update_layout(height=200, showlegend=False, annotations=[dict(text=label, font_size=18, showarrow=False)], margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)


def _donut_tile(progress: float, center_text: str, active_color: str, title: str, subtitle: Optional[str] = None, center_font_size: int = 14):
    p = max(0.0, min(1.0, float(progress or 0.0)))
    fig = go.Figure(data=[
        go.Pie(values=[p, max(0.0, 1.0 - p)], hole=0.74, marker=dict(colors=[active_color, 'rgba(255,255,255,0.08)']), textinfo='none')
    ])
    fig.update_layout(
        height=185,
        showlegend=False,
        annotations=[dict(text=center_text, font_size=center_font_size, showarrow=False)],
        margin=dict(l=4, r=4, t=4, b=4),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{title}" + (f" • {subtitle}" if subtitle else ""))


def _donut_bipolar(value_ratio: float, center_text: str, title: str, pos_color: str = '#22c55e', neg_color: str = '#ef4444', center_font_size: int = 13):
    """Render a bipolar donut starting at 12 o'clock.
    Positive values (>=0) go clockwise in green; negative go counterclockwise in red.
    value_ratio is clipped to [-1, 1].
    """
    v = max(-1.0, min(1.0, float(value_ratio or 0.0)))
    direction = 'clockwise' if v >= 0 else 'counterclockwise'
    color = pos_color if v >= 0 else neg_color
    arc = abs(v)
    # Build donut with arc and remainder
    fig = go.Figure(data=[
        go.Pie(values=[arc, max(0.0, 1.0 - arc)],
               hole=0.70,
               marker=dict(colors=[color, 'rgba(255,255,255,0.08)']),
               textinfo='none',
               direction=direction,
               sort=False)
    ])
    fig.update_layout(
        height=240,
        showlegend=False,
        annotations=[dict(text=center_text, font_size=center_font_size, showarrow=False)],
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    # Set 12 o'clock as start
    fig.update_traces(rotation=270)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(title)


def _render_top_three_donuts(account_info: Dict):
    equity_val = float(account_info.get('equity', 0) or 0)
    balance_val = float(account_info.get('balance', 0) or 0)
    profit_val = float(account_info.get('profit', 0) or 0)
    # Baseline/SoD
    baseline = float(os.getenv('MT5_BASELINE_EQUITY', '200000') or 200000)
    sod_key = f"adv19_sod_{datetime.now().strftime('%Y%m%d')}"
    sod_equity = float(st.session_state.get(sod_key, equity_val) or equity_val)
    daily_profit_pct = float(st.session_state.get('adv19_daily_profit_pct', 1.0))
    daily_risk_pct = float(st.session_state.get('adv19_daily_risk_pct', 3.0))

    # Pull risk envelope from API for consistency
    risk_env = {}
    try:
        risk_env = safe_api_call("GET", "api/v1/account/risk") or {}
    except Exception:
        risk_env = {}
    # Cache for access in same and later renders
    try:
        st.session_state['adv19_risk_env'] = risk_env
    except Exception:
        pass
    # Compute normalized day PnL vs target/loss.
    # Prefer API-provided absolute amounts, fallback to pct-based calc.
    pos_scale = daily_profit_pct / 100.0 if daily_profit_pct > 0 else 0.01
    neg_scale = daily_risk_pct / 100.0 if daily_risk_pct > 0 else 0.01
    api_target_amt = risk_env.get('target_amount') if isinstance(risk_env.get('target_amount'), (int, float)) else None
    api_loss_amt = risk_env.get('loss_amount') if isinstance(risk_env.get('loss_amount'), (int, float)) else None
    # Compute target/loss amounts
    target_amt = api_target_amt if api_target_amt is not None else (sod_equity * pos_scale if sod_equity else 0.0)
    loss_cap_amt = api_loss_amt if api_loss_amt is not None else (sod_equity * neg_scale if sod_equity else 0.0)
    if profit_val >= 0:
        pnl_ratio = min(1.0, (profit_val / target_amt) if target_amt > 0 else 0.0)
    else:
        pnl_ratio = -min(1.0, (abs(profit_val) / loss_cap_amt) if loss_cap_amt > 0 else 0.0)

    # Build feeds with graceful fallbacks (awaiting feed → track)
    balance_feed = {
        'balance_now': balance_val,
        'pnl_total_pct': None,  # awaiting feed
        'pnl_30d_pct': None,
        'pnl_ytd_pct': None,
    }
    equity_feed = {
        'equity_sod': sod_equity,
        'session_pnl': profit_val,
        'pct_to_target': pnl_ratio,  # already normalized −1..+1 toward goal/loss
        'risk_used_pct': None,  # awaiting feed unless provided by backend
        'exposure_pct': None,
    }
    trade_feed = {
        'pnl_day_vs_goal': pnl_ratio,
        'realized_usd': None,
        'unrealized_usd': None,
        'profit_efficiency': None,
        'eff_trend_15m': 0,
    }

    # Pre‑Flight Checklist (sidebar, non-blocking)
    today_key = f"adv19_preflight::{datetime.now().strftime('%Y-%m-%d')}"
    with st.sidebar.expander("🛫 Pre‑Flight Checklist", expanded=not st.session_state.get(today_key, False)):
        st.caption("Confirm before trading starts")
        c1 = st.checkbox("News checked", key=f"pf_news_{today_key}")
        c2 = st.checkbox("Reviewed yesterday", key=f"pf_review_{today_key}")
        c3 = st.checkbox("Focus: Patience", key=f"pf_focus_{today_key}")
        c4 = st.checkbox("Risk controls set", key=f"pf_risk_{today_key}")
        all_ok = c1 and c2 and c3 and c4
        if st.button("Start Session", key=f"pf_btn_{today_key}", disabled=not all_ok):
            st.session_state[today_key] = True
            st.success("Session ready")

    # Move Pulse Decision Surface to the top for at‑a‑glance view
    st.subheader("🎯 Pulse Decision Surface")
    try:
        render_pulse_tiles(pulse_manager)
    except Exception:
        st.info("Decision surface unavailable")
    st.markdown("---")

    # Two primary donuts: Behavioral Compass and Session Vitals (aligned)
    st.subheader("🧭 Behavioral Compass • 🫀 Session Vitals")
    try:
        ms = safe_api_call("GET", "api/v1/mirror/state") or {}
    except Exception:
        ms = {}
    # risk_env already fetched above
    # Risk/exposure hints from risk summary if available
    risk_used = None
    exposure = None
    try:
        rs = st.session_state.get('adv19_risk_last') or {}
        # Attempt to normalize to 0..1 if provided in percent
        ru = rs.get('daily_risk_used') or rs.get('risk_used_pct')
        if ru is not None:
            ru = float(ru)
            risk_used = ru/100.0 if ru > 1.0 else max(0.0, min(1.0, ru))
        ex = rs.get('exposure_pct')
        if ex is not None:
            ex = float(ex)
            exposure = ex/100.0 if ex > 1.0 else max(0.0, min(1.0, ex))
    except Exception:
        pass
    c_left, c_right = st.columns(2)
    with c_left:
        fig_compass = make_behavioral_compass(
            discipline=ms.get('discipline') or 100,
            patience_ratio=ms.get('patience_ratio') or 0,
            efficiency=ms.get('efficiency') or 0,
            conviction_hi_win=ms.get('conviction_hi_win') or 0,
            conviction_lo_loss=ms.get('conviction_lo_loss') or 0,
            pnl_norm=pnl_ratio,
            title="Behavioral Compass",
            subtitle="Keep red covered; tempo in check",
        )
        st.plotly_chart(fig_compass, use_container_width=True, config={'displayModeBar': False})
        st.caption("Outer: Discipline • Mid: Patience/Efficiency • Inner: Conviction")
    with c_right:
        # Three‑donut Session Vitals
        try:
            # live prev_close from balance feed if present
            bal_feed = safe_api_call('GET', 'api/v1/feed/balance') or {}
            prev_close = None
            try:
                prev_close = (bal_feed.get('markers') or {}).get('prev_close')
            except Exception:
                prev_close = None
            target_amt = risk_env.get('target_amount') if isinstance(risk_env.get('target_amount'), (int, float)) else None
            loss_amt = risk_env.get('loss_amount') if isinstance(risk_env.get('loss_amount'), (int, float)) else None
            exposure = (st.session_state.get('adv19_risk_last') or {}).get('exposure_pct')
            d = int(ms.get('discipline') or 0)
            p = int(ms.get('patience_ratio') or 0)
            e = int(ms.get('efficiency') or 0)
            f1, f2, f3 = make_three_vitals(
                equity_usd=equity_val, sod_equity_usd=(sod_equity_api or sod_equity), baseline_equity_usd=baseline,
                target_amount_usd=target_amt, loss_amount_usd=loss_amt,
                exposure_pct=exposure, prev_close_equity_usd=prev_close,
                discipline=d, patience=p, efficiency=e, size=280)
            d1, d2, d3 = st.columns(3)
            with d1:
                st.plotly_chart(f1, use_container_width=True, config={'displayModeBar': False})
                st.caption("Equity vs SoD/Prev Close")
            with d2:
                st.plotly_chart(f2, use_container_width=True, config={'displayModeBar': False})
                st.caption("Exposure • P&L vs target/cap")
            with d3:
                st.plotly_chart(f3, use_container_width=True, config={'displayModeBar': False})
                st.caption("Behavior: Patience • Discipline • Efficiency")
        except Exception:
            st.info("Vitals unavailable")

    # Unified Whisperer block (compass, patterns, vitals, trajectory, whisperer, tiles)
    # Already rendered compass/vitals above; here render the remainder (patterns, trajectory, whisperer, tiles)
    try:
        # Pattern Watch under the donuts
        try:
            patt = safe_api_call("GET", "api/v1/behavioral/patterns") or {}
        except Exception:
            patt = {}
        st.subheader("🧩 Pattern Watch")
        if isinstance(patt, dict) and patt:
            cols = st.columns(3)
            def _chip(active, label, note):
                color = ('#EF4444' if active else '#22C55E')
                st.markdown(f"<div style='display:inline-block;padding:6px 10px;border-radius:14px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);color:{color}'>{label}: {'ON' if active else 'OK'} {('• '+note) if (note and active) else ''}</div>", unsafe_allow_html=True)
            with cols[0]:
                p = patt.get('revenge_trading') or {}
                _chip(bool(p.get('active')), 'Revenge', p.get('note') or '')
            with cols[1]:
                p = patt.get('fomo') or {}
                _chip(bool(p.get('active')), 'FOMO', p.get('note') or '')
            with cols[2]:
                p = patt.get('fear_cut_winners') or {}
                _chip(bool(p.get('active')), 'Fear (cut winners)', p.get('note') or '')
        # Session Trajectory (full)
        st.subheader("📈 Session Trajectory")
        series = _fetch_equity_series_df()
        if not series.empty:
            figT = go.Figure()
            figT.add_trace(go.Scatter(x=series['time'], y=series['pnl'], mode='lines', name='P&L',
                                      line=dict(color='#22C55E', width=2), fill='tozeroy',
                                      fillcolor='rgba(34,197,94,0.1)'))
            figT.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.3)
            figT.update_layout(height=300, margin=dict(t=0,b=20,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(figT, use_container_width=True)
        else:
            st.info("No trades today — trajectory will appear once trades close.")
    except Exception:
        pass


def _render_performance_tiles(account_info: Dict, risk_summary: Dict):
    equity_val = float(account_info.get('equity', 0) or 0)
    balance_val = float(account_info.get('balance', 0) or 0)
    profit_val = float(account_info.get('profit', 0) or 0)
    # Pull session parameters
    daily_profit_pct = float(st.session_state.get('adv19_daily_profit_pct', 1.0))
    daily_risk_pct = float(st.session_state.get('adv19_daily_risk_pct', 3.0))
    # Compute SoD (start-of-day) equity from session cache
    sod_key = f"adv19_sod_{datetime.now().strftime('%Y%m%d')}"
    sod_equity = float(st.session_state.get(sod_key, equity_val) or equity_val)
    # PnL vs Daily Profit Target (donut with PnL inside)
    target_amt = sod_equity * (daily_profit_pct / 100.0) if sod_equity else 0.0
    pnl_prog = (max(0.0, profit_val) / target_amt) if target_amt > 0 else 0.0
    # Balance growth since SoD (map full ring to +20%)
    bal_growth = (balance_val - sod_equity) / sod_equity if sod_equity else 0.0
    bal_growth_prog = max(0.0, min(1.0, bal_growth / 0.20))

    col1, col2 = st.columns(2)
    with col1:
        _donut_tile(
            progress=pnl_prog,
            center_text=f"${profit_val:,.0f}",
            active_color='#22c55e',
            title='Target Progress',
            subtitle=f"{int(pnl_prog*100) if target_amt>0 else 0}% of ${target_amt:,.0f}"
        )
    with col2:
        delta_bal = balance_val - sod_equity
        _donut_tile(
            progress=bal_growth_prog,
            center_text=(f"+${delta_bal:,.0f}" if delta_bal >= 0 else f"-${abs(delta_bal):,.0f}"),
            active_color='#a78bfa',
            title='Balance since SoD',
            subtitle=f"Start ${sod_equity:,.0f} • Full ring +20%"
        )

def get_trait_history(limit: int = 20) -> List[Dict]:
    """Fetch recent behavioral traits/incidents (no mocks)."""
    res = safe_api_call("GET", f"psych/traits/history?limit={limit}")
    if isinstance(res, list):
        return res
    if isinstance(res, dict) and isinstance(res.get("items"), list):
        return res["items"]
    return []

def render_psychology_insights_panel(confluence_data: Dict, risk_summary: Dict):
    """Render session mindset panel"""
    # Accept None and other shapes gracefully
    if not isinstance(confluence_data, dict):
        confluence_data = {}
    if not isinstance(risk_summary, dict):
        risk_summary = {}
    
    st.subheader("🧠 SESSION MINDSET")
    
    confluence_score = confluence_data.get("score", 75)
    consecutive_losses = risk_summary.get("consecutive_losses", 0)
    trades_today = risk_summary.get("trades_used", 0)
    risk_phase = risk_summary.get("risk_phase", "stable")
    
    insights = create_psychology_insights(
        confluence_score, consecutive_losses, trades_today, risk_phase
    )
    
    for insight in insights:
        st.markdown(f'<div class="psychology-insight">{insight}</div>', 
                   unsafe_allow_html=True)
    
    # Trading principles (dynamic-ready: fetch from API if available)
    principles = []
    try:
        resp = safe_api_call("GET", "principles/titz")
        if isinstance(resp, dict) and resp.get("items"):
            principles = resp.get("items", [])
    except Exception:
        principles = []
    if not principles:
        principles = [
            "Think in probabilities, not predictions",
            "Focus on process over outcomes",
            "Accept uncertainty as natural",
            "Maintain emotional discipline",
            "Stick to your risk management rules",
        ]
    # Trait history timeline (subtle)
    try:
        traits = get_trait_history(10)
    except Exception:
        traits = []
    if traits:
        st.markdown("**Recent Traits:**")
        for t in traits:
            ts = t.get("time") or t.get("timestamp")
            try:
                tdisp = pd.to_datetime(ts, errors="coerce").strftime("%Y-%m-%d %H:%M") if ts else "—"
            except Exception:
                tdisp = "—"
            label = t.get("name") or t.get("trait") or "trait"
            val = t.get("value") or t.get("score") or ""
            st.caption(f"{tdisp} • {label} {val}")

def render_pulse_tiles(pulse_manager: AdvancedPulseRiskManager):
    """Render Pulse-specific tiles with error handling"""
    st.subheader("🎯 Pulse Decision Surface")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Confluence Score Tile
    with col1:
        confluence_data = pulse_manager.get_confluence_score()
        score = confluence_data.get("score", 0)
        grade = confluence_data.get("grade", "Unknown")
        band = _confluence_band(score)
        st.markdown(f"""
        <div class="pulse-tile tile-{band}">
            <h4>Confluence Score</h4>
            <h2>{score}/100</h2>
            <p>Grade: {grade}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Explain Score", key="explain_confluence"):
            with st.expander("Score Breakdown", expanded=True):
                reasons = confluence_data.get("reasons", [])
                if reasons:
                    for reason in reasons:
                        st.write(f"• {reason}")
                else:
                    st.write("No specific reasons available")
                # Component scores
                components = confluence_data.get("component_scores", {})
                if components:
                    st.write("**Component Analysis:**")
                    for component, comp_score in components.items():
                        st.write(f"- {component.upper()}: {comp_score}")

    # Market Bias Tile
    with col2:
        bias_cls = _bias_class(score)
        bias = "Bull" if bias_cls == "bull" else "Bear" if bias_cls == "bear" else "Neutral"
        bias_icon = "🟢" if bias_cls == "bull" else "🔴" if bias_cls == "bear" else "🟡"
        st.markdown(f"""
        <div class="pulse-tile tile-{bias_cls}">
            <h4>Market Bias</h4>
            <h2>{bias_icon} {bias}</h2>
            <p>Confidence: {score}%</p>
        </div>
        """, unsafe_allow_html=True)

    # Risk Remaining Tile
    with col3:
        risk_data = pulse_manager.get_risk_summary()
        risk_remaining = risk_data.get("risk_left", 0)
        st.markdown(f"""
        <div class="pulse-tile tile-plain">
            <h4>Risk Remaining</h4>
            <h2>{risk_remaining:.1f}%</h2>
            <p>Daily Budget</p>
        </div>
        """, unsafe_allow_html=True)

    # Suggested R:R Tile
    with col4:
        suggested_rr = 2.0 if score > 70 else 1.5 if score > 50 else 1.2
        st.markdown(f"""
        <div class="pulse-tile tile-plain">
            <h4>Suggested R:R</h4>
            <h2>{suggested_rr}:1</h2>
            <p>Based on Score</p>
        </div>
        """, unsafe_allow_html=True)

def render_opportunities(pulse_manager: AdvancedPulseRiskManager):
    """Render top trading opportunities with error handling"""
    st.subheader("🎯 Top Trading Opportunities")
    
    try:
        opportunities = pulse_manager.get_top_opportunities(3)
        
        for opp in opportunities:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{opp['symbol']}** - Score: {opp['score']}")
                    st.write(f"Bias: {opp.get('bias', 'Neutral')}")
                
                with col2:
                    st.write(f"R:R: {opp.get('rr', '—')}")
                    st.write(f"SL: {opp.get('sl', '—')}")
                
                with col3:
                    st.write(f"TP: {opp.get('tp', '—')}")
                    
                    if st.button(f"Analyze {opp['symbol']}", key=f"analyze_{opp['symbol']}"):
                        st.info(f"Opening analysis for {opp['symbol']}...")
                
                # Expandable reasons
                with st.expander("📋 Analysis Details"):
                    reasons = opp.get("reasons", [])
                    if reasons:
                        for reason in reasons:
                            st.write(f"• {reason}")
                    else:
                        st.write("No specific analysis available")
            
            st.divider()
    
    except Exception as e:
        st.error(f"Unable to load opportunities: {str(e)}")

def render_behavioral_insights(pulse_manager: AdvancedPulseRiskManager):
    """Render behavioral trading insights"""
    st.subheader("🧠 Behavioral Insights")
    
    try:
        risk_data = pulse_manager.get_risk_summary()
        warnings = risk_data.get("warnings", [])
        
        if warnings:
            st.warning("**Active Behavioral Alerts:**")
            for warning in warnings:
                st.write(f"⚠️ {warning}")
        else:
            st.success("✅ No behavioral alerts")
        
        # Trading principles reminder
        with st.expander("📚 Trading in the Zone Principles"):
            st.write("✅ Think in probabilities, not predictions")
            st.write("✅ Focus on process over outcomes")
            st.write("✅ Accept uncertainty as natural")
            st.write("✅ Maintain emotional discipline")
            st.write("✅ Stick to your risk management rules")
    
    except Exception as e:
        st.error(f"Error loading behavioral insights: {e}")

def _kafka_consumer():
    """Create a Kafka consumer if env vars are set; else return None."""
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("KAFKA_TRADES_TOPIC")
    if not bootstrap or not topic:
        return None
    try:
        from confluent_kafka import Consumer
        conf = {
            'bootstrap.servers': bootstrap,
            'group.id': os.getenv('KAFKA_GROUP_ID', 'pulse-risk'),
            'auto.offset.reset': 'latest',
            'enable.auto.commit': False,
        }
        return Consumer(conf)
    except Exception:
        return None

def _read_last_trade_from_kafka(timeout_sec: float = 1.0) -> Optional[Dict]:
    consumer = _kafka_consumer()
    topic = os.getenv("KAFKA_TRADES_TOPIC")
    if not consumer or not topic:
        return None
    try:
        consumer.subscribe([topic])
        msg = consumer.poll(timeout=timeout_sec)
        if msg is None or msg.error():
            return None
        payload = msg.value()
        if not payload:
            return None
        try:
            data = json.loads(payload.decode('utf-8')) if isinstance(payload, (bytes, bytearray)) else json.loads(payload)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    except Exception:
        return None
    finally:
        try:
            consumer.close()
        except Exception:
            pass

def _read_last_trade_via_api() -> Optional[Dict]:
    """Try MT5 bridge-like endpoints via API for the most recent trade (no mocks)."""
    candidates = [
        "history_deals_get?limit=1",
        "history_orders_get?limit=1",
    ]
    best: Optional[Tuple[pd.Timestamp, Dict]] = None
    for ep in candidates:
        try:
            data = safe_api_call("GET", ep)
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                # normalize time
                ts = None
                for col in ["time", "time_msc", "time_done", "time_close", "timestamp"]:
                    if col in df.columns:
                        try:
                            if col in ("time", "time_done", "time_close", "timestamp"):
                                ts_series = pd.to_datetime(df[col], errors="coerce")
                            else:
                                ts_series = pd.to_datetime(df[col], unit='s', errors="coerce")
                            df["_ts"] = ts_series
                            break
                        except Exception:
                            pass
                if "_ts" in df.columns:
                    i = df["_ts"].idxmax()
                    ts = df.loc[i, "_ts"]
                    trade = df.loc[i].to_dict()
                    if ts is not None:
                        if best is None or ts > best[0]:
                            best = (ts, trade)
        except Exception:
            continue
    return best[1] if best else None

def _fetch_equity_series_df() -> pd.DataFrame:
    try:
        data = safe_api_call("GET", "api/v1/feed/equity/series") or {}
        pts = data.get('points') if isinstance(data, dict) else []
        if not isinstance(pts, list) or not pts:
            return pd.DataFrame()
        df = pd.DataFrame(pts)
        df['time'] = pd.to_datetime(df.get('ts'), errors='coerce')
        df['pnl'] = pd.to_numeric(df.get('pnl'), errors='coerce')
        return df.dropna(subset=['time'])
    except Exception:
        return pd.DataFrame()

def _render_unified_whisperer_block(account_info: Dict, risk_env: Dict):
    # Behavioral Compass and Pattern Watch side-by-side
    try:
        mirror = safe_api_call("GET", "api/v1/mirror/state") or {}
    except Exception:
        mirror = {}
    try:
        patt = safe_api_call("GET", "api/v1/behavioral/patterns") or {}
    except Exception:
        patt = {}
    colA, colB = st.columns(2)
    with colA:
        st.subheader("🎯 Behavioral Compass")
        metrics = [
            {'name': 'Discipline', 'value': int(mirror.get('discipline') or 0), 'color': '#22C55E'},
            {'name': 'Patience', 'value': int(mirror.get('patience_ratio') or 0), 'color': '#3B82F6'},
            {'name': 'Efficiency', 'value': int(mirror.get('efficiency') or 0), 'color': '#06B6D4'},
            {'name': 'Conviction', 'value': int(mirror.get('conviction_hi_win') or 0), 'color': '#8B5CF6'},
        ]
        fig = go.Figure()
        for i, m in enumerate(metrics):
            fig.add_trace(go.Pie(values=[m['value'], 100-m['value']], hole=0.4 + i*0.1,
                                 marker=dict(colors=[m['color'], 'rgba(31,41,55,0.3)']),
                                 textinfo='none', showlegend=False,
                                 domain=dict(x=[0.1*i, 1-0.1*i], y=[0.1*i, 1-0.1*i]),
                                 hovertemplate=f"{m['name']}: {m['value']}%<extra></extra>"))
        try:
            import numpy as _np
            overall = int(_np.mean([m['value'] for m in metrics]))
        except Exception:
            overall = int(sum([m['value'] for m in metrics])/len(metrics)) if metrics else 0
        fig.add_annotation(text=f"<b>{overall}%</b><br>Overall", x=0.5, y=0.5, showarrow=False, font=dict(size=20, color='white'))
        fig.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        st.subheader("🧩 Pattern Watch")
        chips = [
            ('Revenge Trading', patt.get('revenge_trading') or {}),
            ('FOMO', patt.get('fomo') or {}),
            ('Fear (Cut Winners)', patt.get('fear_cut_winners') or {}),
        ]
        for label, obj in chips:
            active = bool(obj.get('active'))
            note = obj.get('note') or ''
            color = '#EF4444' if active else '#22C55E'
            status = 'ALERT' if active else 'OK'
            st.markdown(
                f"<div style='padding:8px;margin:4px 0;background:rgba(31,41,55,0.3);border-left:3px solid {color};border-radius:0 6px 6px 0;'>"
                f"<span style='color:#9CA3AF;'>{label}:</span> "
                f"<span style='color:{color};font-weight:700'>{status}</span>"
                f"<span style='color:#9CA3AF;'> {'• ' + note if (note and active) else ''}</span>"
                f"</div>",
                unsafe_allow_html=True)

    # Session Vitals: same size as compass (rendered separately)
    st.subheader("💰 Session Vitals")
    try:
        eq = float(account_info.get('equity') or 0)
        bal = float(account_info.get('balance') or 0)
        sod = float(risk_env.get('sod_equity') or bal or eq)
        target_amt = risk_env.get('target_amount') if isinstance(risk_env.get('target_amount'), (int, float)) else None
        loss_amt = risk_env.get('loss_amount') if isinstance(risk_env.get('loss_amount'), (int, float)) else None
        daily_profit_pct = float(risk_env.get('daily_profit_pct') or 0.0)
        daily_risk_pct = float(risk_env.get('daily_risk_pct') or 0.0)
        fig_sess = donut_session_vitals(
            equity_usd=eq,
            sod_equity_usd=sod,
            baseline_equity_usd=bal or sod,
            daily_profit_pct=daily_profit_pct,
            daily_risk_pct=daily_risk_pct,
            target_amount_usd=target_amt,
            loss_amount_usd=loss_amt,
            size=(280, 280),
        )
        st.plotly_chart(fig_sess, use_container_width=True, config={'displayModeBar': False})
    except Exception:
        st.info("Vitals unavailable")

    # Session Trajectory
    st.subheader("📈 Session Trajectory")
    series = _fetch_equity_series_df()
    if not series.empty:
        figT = go.Figure()
        figT.add_trace(go.Scatter(x=series['time'], y=series['pnl'], mode='lines', name='P&L',
                                  line=dict(color='#22C55E', width=2), fill='tozeroy',
                                  fillcolor='rgba(34,197,94,0.1)'))
        figT.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.3)
        figT.update_layout(height=300, margin=dict(t=0,b=20,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(figT, use_container_width=True)
    else:
        st.info("No trades today — trajectory will appear once trades close.")

    # Discipline Posture (wired to /api/v1/discipline/summary)
    st.subheader("📊 Discipline Posture")
    try:
        dsum = safe_api_call('GET', 'api/v1/discipline/summary') or {}
        today_score = dsum.get('today')
        series7 = dsum.get('seven_day') or []
        cdp1, cdp2 = st.columns([1,2])
        with cdp1:
            if today_score is not None:
                st.metric("Today", f"{float(today_score):.0f}%")
        with cdp2:
            if isinstance(series7, list) and series7:
                import pandas as _pd
                df7 = _pd.DataFrame(series7)
                if 'date' in df7 and 'score' in df7:
                    df7['date'] = _pd.to_datetime(df7['date'], errors='coerce')
                    figD = go.Figure(go.Bar(x=df7['date'], y=df7['score'], marker_color=['#22C55E' if x>=70 else '#FBBF24' if x>=50 else '#EF4444' for x in df7['score']]))
                    figD.update_layout(height=180, margin=dict(t=10,b=10,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(figD, use_container_width=True)
            else:
                st.caption("No history yet")
    except Exception:
        st.info("Discipline summary unavailable")

    # The Whisperer (reuse component)
    st.subheader("🤖 The Whisperer")
    try:
        render_whisper_panel(api=os.getenv("DJANGO_API_URL", "http://django:8000").rstrip('/') + "/api/pulse/whispers")
    except Exception:
        st.info("Whisperer unavailable")

    # Bottom tiles
    st.divider()
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        st.markdown("### Trade Quality")
        try:
            ph = safe_api_call('GET', 'api/v1/profit-horizon') or []
            items = ph if isinstance(ph, list) else ph.get('items') or []
            wins = sum(1 for x in items if (float(x.get('pnl_usd') or 0) > 0))
            losses = sum(1 for x in items if (float(x.get('pnl_usd') or 0) < 0))
            st.metric("Wins", f"{wins}")
            st.metric("Losses", f"{losses}")
        except Exception:
            st.info("Unavailable")
    with bc2:
        st.markdown("### Profit Efficiency")
        try:
            ph = safe_api_call('GET', 'api/v1/profit-horizon') or []
            items = ph if isinstance(ph, list) else ph.get('items') or []
            total_peak = 0.0
            total_pnl = 0.0
            for it in items:
                peak = float(it.get('peak_usd') or 0)
                pnlv = float(it.get('pnl_usd') or 0)
                if peak > 0 and pnlv > 0:
                    total_peak += peak
                    total_pnl += pnlv
            eff = (total_pnl / total_peak) if total_peak > 0 else None
            if eff is not None:
                st.metric("Captured vs Potential", f"{eff*100:.0f}%")
            else:
                st.metric("Captured vs Potential", "—")
                st.caption("Awaiting positive trades")
        except Exception:
            st.metric("Captured vs Potential", "—")
    with bc3:
        st.markdown("### Risk Management")
        try:
            used = risk_env.get('used_pct')
            exp = risk_env.get('exposure_pct')
            def _norm(x):
                if x is None: return None
                x = float(x)
                return x if x <= 1.0 else x/100.0
            used_n = _norm(used)
            exp_n = _norm(exp)
            st.metric("Risk Used", f"{(used_n*100):.0f}%" if used_n is not None else "—")
            st.metric("Exposure", f"{(exp_n*100):.0f}%" if exp_n is not None else "—")
        except Exception:
            st.metric("Risk Used", "—")
            st.metric("Exposure", "—")
    with bc4:
        st.markdown("### Session Momentum")
        try:
            series2 = _fetch_equity_series_df()
            if not series2.empty and len(series2) > 2:
                df = series2.tail(min(20, len(series2)))
                inc = (df['pnl'].diff() > 0).mean()
                st.metric("Positive Momentum", f"{inc*100:.0f}%")
                st.caption("Last ~20 points")
            else:
                st.metric("Positive Momentum", "—")
                st.caption("Awaiting series")
        except Exception:
            st.metric("Positive Momentum", "—")

def get_last_trade_snapshot() -> Dict:
    """Return last trade from API, falling back to Kafka if configured."""
    snap = _read_last_trade_via_api() or _read_last_trade_from_kafka()
    return snap or {}

def _fetch_ohlc(symbol: str, tf: str) -> pd.DataFrame:
    """Fetch OHLC data via yfinance for common timeframes including 15m."""
    # Use only valid yfinance intervals and resample for 4h
    tf_map = {
        '15m': ('7d', '15m'),
        '1h': ('30d', '60m'),
        '4h': ('60d', '60m'),  # fetch 60m then resample to 4H
        '1d': ('1y', '1d'),
    }
    period, interval = tf_map.get(tf, ('30d', '60m'))
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
        # Fallback for some FX/indices where 15m may be spotty: try 30m
        if (df is None or df.empty) and tf == '15m':
            df = yf.download(symbol, period='14d', interval='30m', auto_adjust=False, progress=False)
        if isinstance(df, pd.DataFrame) and not df.empty:
            df = df.rename(columns=str.title)
            df = df[['Open','High','Low','Close','Volume']]
            df = df.dropna()
            # Resample to 4H if requested
            if tf == '4h':
                try:
                    df = df.resample('4H').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum',
                    }).dropna()
                except Exception:
                    pass
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def render_technical_analysis_panel():
    st.subheader("📈 Technical Analysis")
    colA, colB, colC = st.columns([3,1,1])
    with colA:
        # Use platform symbols as primary labels; map to yfinance tickers internally
        instruments = [
            ("EURUSD", "EURUSD=X"),
            ("GBPUSD", "GBPUSD=X"),
            ("USDJPY", "USDJPY=X"),
            ("EURGBP", "EURGBP=X"),
            ("XAUUSD", "XAUUSD=X"),  # Spot gold vs USD
            ("SPX500", "^GSPC"),
            ("BTCUSD", "BTC-USD"),
            ("ETHUSD", "ETH-USD"),
        ]
        selected = st.selectbox("Select Instrument", options=instruments, index=0, format_func=lambda x: x[0])
        symbol_label, symbol = selected
    with colB:
        tf = st.selectbox("Timeframe", options=["15m","1h","4h","1d"], index=0)
    with colC:
        highlight_mondays = st.checkbox("Highlight Mondays", value=False)

    with st.spinner("Loading chart…"):
        df = _fetch_ohlc(symbol, tf)
    if df is None or df.empty:
        st.info("No data available for chart.")
        return

    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name=symbol_label
    )])
    # Add simple MAs for context
    try:
        ma_fast = df['Close'].rolling(10).mean()
        ma_slow = df['Close'].rolling(30).mean()
        fig.add_trace(go.Scatter(x=df.index, y=ma_fast, mode='lines', name='MA10', line=dict(color='#10B981', width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=ma_slow, mode='lines', name='MA30', line=dict(color='#F59E0B', width=1.5)))
    except Exception:
        pass

    if highlight_mondays:
        try:
            mondays = [ts for ts in df.index if ts.weekday() == 0]
            for ts in mondays:
                fig.add_vline(x=ts, line=dict(color='rgba(255,255,255,0.25)', width=1, dash='dot'))
        except Exception:
            pass

    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Lightweight analysis notes (local only)
    with st.expander("📝 Analysis Notes", expanded=False):
        key = f"ta_notes_{symbol}_{tf}"
        existing = st.session_state.get(key, "")
        notes = st.text_area("Notes", value=existing, height=120)
        if st.button("Save Notes", key=f"save_{key}"):
            st.session_state[key] = notes
            st.success("Saved.")

def main():
    """Main dashboard function with comprehensive error handling"""
    
    # Title removed per request
    # st.title("Zanalytics Pulse — Advanced Risk Manager")

    # IniOkay, now the OX3 macro works pretty well, but it's showing that it's showing different instruments. It doesn't show that it's only one year to one day periods. I just wanted to check if it's possible to change the 16 and 19. So now it's just showing something else. So it shows something more like 16 and 19. So I just wanted to check. If we can use the same symbols as in the 03 macro in the news dashboard, because it's got slash not equals X. It's got the correct ticker symbol. Also, there is control power takes to positional argument a 3-word command. So that's a mistake.tialize Advanced manager under a distinct key to avoid clashes with page 16
    if 'adv_pulse_manager' not in st.session_state or not isinstance(st.session_state.adv_pulse_manager, AdvancedPulseRiskManager):
        st.session_state.adv_pulse_manager = AdvancedPulseRiskManager()

    pulse_manager = st.session_state.adv_pulse_manager

    # System health status
    health_data = safe_api_call("GET", "pulse/health")
    if isinstance(health_data, dict) and "error" not in health_data:
        status = health_data.get("status", "unknown")
        lag = health_data.get("lag_ms", "—")
        st.caption(f"System Status: {status} | Lag: {lag}ms | Last Update: {datetime.now().strftime('%H:%M:%S')}")
    else:
        err = health_data.get("error") if isinstance(health_data, dict) else "unknown"
        st.caption(f"System Status: offline ({err}) | Last Update: {datetime.now().strftime('%H:%M:%S')}")


    # Controls: Fast Mode + Live Updates (Kafka)
    ctrl_cols = st.columns([1.2, 1.2, 6])
    with ctrl_cols[0]:
        fast_mode = st.checkbox("Fast mode", value=True, help="Prefer cached data and avoid slow calls on load")
    with ctrl_cols[1]:
        live_updates = st.checkbox("Live (Kafka)", value=False, help="Ingest latest trade from Kafka once per refresh")

    # Bridge override (helpful when running Streamlit outside Docker)
    with ctrl_cols[2]:
        current_override = st.session_state.get('adv19_bridge_url', '') or ''
        with st.expander("Bridge URL (override)", expanded=False):
            url_input = st.text_input("MT5 Bridge Base URL", value=current_override, placeholder="e.g. https://api3.zanalytics.app")
            cA, cB, cC = st.columns([1,1,4])
            with cA:
                if st.button("Apply", key="apply_bridge_19"):
                    st.session_state['adv19_bridge_url'] = url_input.strip() or None
                    try:
                        # update live manager candidates immediately
                        if url_input.strip():
                            pulse_manager._mt5_candidates = [url_input.strip()] + [u for u in pulse_manager._mt5_candidates if u and u != url_input.strip()]
                            pulse_manager.mt5_url = url_input.strip()
                    except Exception:
                        pass
                    st.success("Bridge override applied")
            with cB:
                if st.button("Test", key="test_bridge_19"):
                    test_url = (url_input or pulse_manager.mt5_url or "").rstrip('/')
                    if not test_url:
                        st.warning("No URL to test")
                    else:
                        try:
                            r = requests.get(f"{test_url}/account_info", timeout=1.2)
                            if r.ok:
                                st.success("Bridge reachable ✓")
                            else:
                                st.error(f"HTTP {r.status_code}")
                        except Exception as e:
                            st.error(f"Error: {e}")

        api_current = st.session_state.get('adv19_api_base', '') or (os.getenv('DJANGO_API_URL', ''))
        with st.expander("Django API Base (override)", expanded=False):
            api_input = st.text_input("Django API Base URL", value=api_current or '', placeholder="e.g. https://django2.zanalytics.app")
            c1, c2, _ = st.columns([1,1,4])
            with c1:
                if st.button("Apply", key="apply_api_19"):
                    st.session_state['adv19_api_base'] = (api_input or '').strip() or None
                    st.success("API base override applied")
            with c2:
                if st.button("Test", key="test_api_19"):
                    base = (api_input or os.getenv('DJANGO_API_URL', '')).strip().rstrip('/')
                    if not base:
                        st.warning("No URL to test")
                    else:
                        try:
                            r = requests.get(f"{base}/api/v1/market/mini", timeout=1.2)
                            if r.ok:
                                st.success("Django API reachable ✓")
                            else:
                                st.error(f"HTTP {r.status_code}")
                        except Exception as e:
                            st.error(f"Error: {e}")

    # If live updates enabled, try a single non-blocking Kafka poll and write to cache
    if live_updates:
        try:
            msg = _read_last_trade_from_kafka(timeout_sec=0.15)
            if isinstance(msg, dict) and msg:
                # Normalize minimal trade record for cache list
                trade = {
                    'time': msg.get('time') or msg.get('timestamp') or datetime.now().isoformat(),
                    'ticket': msg.get('ticket'),
                    'symbol': msg.get('symbol'),
                    'type': msg.get('type'),
                    'volume': msg.get('volume'),
                    'price': msg.get('price') or msg.get('price_current') or msg.get('price_open'),
                    'profit': msg.get('profit'),
                    'comment': msg.get('comment', 'kafka')
                }
                # Append to cached recent trades (list of dicts)
                key = f"adv19:recent_trades:20:7"
                cached_list = pulse_manager._cache_get(key) or []
                if isinstance(cached_list, list):
                    cached_list = [trade] + cached_list
                    cached_list = cached_list[:50]
                    pulse_manager._cache_set(key, cached_list, ttl_seconds=15)
        except Exception:
            pass
        # gentle auto-refresh to surface live updates
        try:
            time.sleep(1.0)
            st.experimental_rerun()
        except Exception:
            pass

    # Get account information and risk status (prefer fast calls)
    try:
        # If a pure UI event triggered rerun (e.g., slider), avoid network fetch to keep PnL stable
        ui_event = bool(st.session_state.get('_adv19_ui_event', False))

        if not ui_event:
            # First try a single consolidated API call (if available)
            dashboard_data = pulse_manager.get_dashboard_data()
            account_info = dashboard_data.get("account_info") if isinstance(dashboard_data, dict) else None
            # Prefer 'risk_summary' then 'risk_management'
            risk_data = dashboard_data.get("risk_summary") if isinstance(dashboard_data, dict) else None
            if (not isinstance(risk_data, dict)) and isinstance(dashboard_data, dict):
                risk_data = dashboard_data.get("risk_management")
            positions_df = pd.DataFrame(dashboard_data.get("open_positions")) if isinstance(dashboard_data, dict) and isinstance(dashboard_data.get("open_positions"), list) else pd.DataFrame()
            confluence_data = dashboard_data.get("confluence") if isinstance(dashboard_data, dict) else {}
            risk_event = dashboard_data.get("risk_event") if isinstance(dashboard_data, dict) else {}

            # Fallbacks if consolidated endpoint is unavailable
            if not isinstance(account_info, dict) or not account_info:
                account_info = pulse_manager._cache_get("adv19:account_info") if fast_mode else None
                if not isinstance(account_info, dict) or not account_info:
                    account_info = pulse_manager.get_account_info()

            if not isinstance(risk_data, dict) or not risk_data:
                risk_data = pulse_manager._cache_get("adv19:risk_summary") if fast_mode else None
                if not isinstance(risk_data, dict) or not risk_data:
                    risk_data = pulse_manager.get_risk_summary()

            if positions_df.empty:
                cached_pos = pulse_manager._cache_get('adv19:positions') if fast_mode else None
                if isinstance(cached_pos, list) and cached_pos:
                    try:
                        positions_df = pd.DataFrame(cached_pos)
                    except Exception:
                        positions_df = pd.DataFrame()
            if positions_df.empty:
                positions_df = pulse_manager.get_positions()

            # Persist last good values for UI-only reruns
            try:
                st.session_state['adv19_account_info_last'] = account_info or st.session_state.get('adv19_account_info_last') or {}
                st.session_state['adv19_risk_last'] = risk_data or st.session_state.get('adv19_risk_last') or {}
                st.session_state['adv19_positions_last'] = positions_df.to_dict(orient='records') if isinstance(positions_df, pd.DataFrame) else st.session_state.get('adv19_positions_last') or []
                st.session_state['adv19_confluence_last'] = confluence_data or st.session_state.get('adv19_confluence_last') or {}
            except Exception:
                pass
        else:
            # UI-only run: use cached values to prevent PnL flicker on slider interactions
            account_info = st.session_state.get('adv19_account_info_last') or pulse_manager._cache_get("adv19:account_info") or {}
            risk_data = st.session_state.get('adv19_risk_last') or pulse_manager._cache_get("adv19:risk_summary") or {}
            last_positions = st.session_state.get('adv19_positions_last') or pulse_manager._cache_get('adv19:positions') or []
            try:
                positions_df = pd.DataFrame(last_positions)
            except Exception:
                positions_df = pd.DataFrame()
            confluence_data = st.session_state.get('adv19_confluence_last') or {}
            risk_event = st.session_state.get('adv19_risk_event_last') or {}
    except Exception as e:
        st.error(f"Error loading data: {e}")
        account_info = {}
        positions_df = pd.DataFrame()
        risk_data = {}
        confluence_data = {}

    # If account info missing, show connection diagnostics
    if not account_info:
        with st.expander("Connection Diagnostics", expanded=False):
            st.caption(f"MT5 bridge URL: {getattr(pulse_manager, 'mt5_url', '—')}")
            if getattr(pulse_manager, 'status_messages', None):
                for m in pulse_manager.status_messages[-5:]:
                    st.caption(f"• {m}")
            else:
                st.caption("No status messages available.")

    # Minimal Bridge ID line (replace big account bubble)
    bridge_online = bool(account_info)
    server_name = account_info.get("server") or os.getenv("MT5_SERVER") or account_info.get("company") or "—"
    st.caption(f"Bridge: {'Online' if bridge_online else 'Offline'} • Server: {server_name}")

    # Top metrics row (concise, at top)
    balance_val = float(account_info.get('balance', 0) or 0)
    equity_val = float(account_info.get('equity', 0) or 0)
    profit_val = float(account_info.get('profit', 0) or 0)
    margin_level_val = float(account_info.get('margin_level', 0) or 0)

    # Bring back concise text row (no margin): Balance / Equity / PnL
    baseline = float(os.getenv('MT5_BASELINE_EQUITY', '200000') or 200000)
    sod_key = f"adv19_sod_{datetime.now().strftime('%Y%m%d')}"
    sod_equity = float(st.session_state.get(sod_key, equity_val) or equity_val)
    daily_profit_pct = float(st.session_state.get('adv19_daily_profit_pct', 1.0))
    target_amt_top = sod_equity * (daily_profit_pct / 100.0) if sod_equity else 0.0

    t1, t2, t3 = st.columns(3)
    with t1:
        st.metric("Balance", f"${balance_val:,.2f}")
        st.caption(f"Start ${baseline:,.0f}")
    with t2:
        st.metric("Equity", f"${equity_val:,.2f}")
        st.caption(f"SoD ${sod_equity:,.0f}")
    with t3:
        st.metric("PnL", f"${profit_val:,.2f}")
        st.caption(f"Target ${target_amt_top:,.0f}")

    # Top three bipolar donuts below the text row (no extra separators)
    _render_top_three_donuts(account_info)

    # Target progress indicators (below top metrics)
    try:
        lock_ratio_ui = float(st.session_state.get('adv19_lock_ratio', 0.5))
    except Exception:
        lock_ratio_ui = 0.5
    # Ensure risk/target params are defined before use
    daily_risk_pct = float(st.session_state.get('adv19_daily_risk_pct', 3.0))
    daily_profit_pct = float(st.session_state.get('adv19_daily_profit_pct', 1.0))
    risk_cap_amt = equity_val * (daily_risk_pct / 100.0) if equity_val else 0.0
    target_amt = equity_val * (daily_profit_pct / 100.0) if equity_val else 0.0
    per_trade_risk = (equity_val * (daily_risk_pct / 100.0)) / max(int(st.session_state.get('adv19_anticipated_trades', 5)), 1) if equity_val else 0.0
    # Progress to profit target (0..1)
    prog_target = (max(0.0, profit_val) / target_amt) if target_amt > 0 else 0.0
    # R achieved relative to per-trade risk
    r_achieved = (profit_val / per_trade_risk) if per_trade_risk > 0 else 0.0
    # Drawdown vs daily loss cap
    dd_prog = (abs(min(0.0, profit_val)) / risk_cap_amt) if risk_cap_amt > 0 else 0.0
    # Lock preview
    lock_preview = max(0.0, profit_val) * lock_ratio_ui if profit_val > 0 else 0.0

    st.caption(
        f"🎯 Target ${target_amt:,.0f} • Progress {prog_target*100:,.0f}% • {r_achieved:,.2f}R"
    )
    if profit_val < 0 and risk_cap_amt > 0:
        st.caption(
            f"🛑 Drawdown ${abs(profit_val):,.0f} of ${risk_cap_amt:,.0f} cap ({dd_prog*100:,.0f}%)"
        )
    if lock_preview > 0:
        st.caption(
            f"🔒 If trail now at {lock_ratio_ui*100:,.0f}% → lock ${lock_preview:,.0f}"
        )

    # Performance donuts at the top
    st.markdown("---")
    # (Removed) auxiliary performance donuts

    # Advanced Risk Control Panel (with 3D allocation)
    render_risk_control_panel(account_info, risk_data)

    # Whisperer: Discipline Posture (replaces 3D impact in spirit)
    st.subheader("🧭 Discipline Posture")
    _render_discipline_posture(risk_data)

    # Key info derived from risk controls for quick guardrails
    equity_val = float(account_info.get('equity', 0) or 0)
    daily_risk_pct = float(st.session_state.get('adv19_daily_risk_pct', 3.0))
    daily_profit_pct = float(st.session_state.get('adv19_daily_profit_pct', 1.0))
    max_allowed_loss_amt = equity_val * (daily_risk_pct / 100.0)
    daily_profit_target_amt = equity_val * (daily_profit_pct / 100.0)

    info_cols = st.columns(4)
    with info_cols[0]:
        st.metric("Max Allowed Loss (info)", f"${max_allowed_loss_amt:,.0f}", f"{daily_risk_pct:.1f}%")
    with info_cols[1]:
        # Start-of-Day equity (session-persisted)
        sod_key = f"adv19_sod_{datetime.now().strftime('%Y%m%d')}"
        if sod_key not in st.session_state and equity_val > 0:
            st.session_state[sod_key] = equity_val
        sod_equity = float(st.session_state.get(sod_key, equity_val) or 0)
        st.metric("Start-of-Day Equity", f"${sod_equity:,.0f}")
    with info_cols[2]:
        st.metric("Daily Profit Target", f"${daily_profit_target_amt:,.0f}", f"{daily_profit_pct:.1f}%")
    with info_cols[3]:
        hit = equity_val >= (sod_equity + daily_profit_target_amt) if (sod_equity and daily_profit_target_amt) else False
        st.metric("Target Status", "Hit" if hit else "—")

    # Place Open Positions directly below risk controls
    positions_df = positions_df if 'positions_df' in locals() else pd.DataFrame()
    if isinstance(positions_df, pd.DataFrame) and not positions_df.empty:
        st.subheader("📋 Open Positions")
        # Normalize and format
        df = positions_df.copy()
        if 'type' in df.columns:
            df['type'] = df['type'].map({0: 'BUY', 1: 'SELL'}).fillna(df['type'])
        for col in ['volume', 'price_open', 'price_current']:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').round(2)
                except Exception:
                    pass
        # Parse time
        opened_at = None
        if 'time' in df.columns:
            try:
                df['time'] = pd.to_datetime(df['time'], errors='coerce')
            except Exception:
                pass

        def _session_for(ts: Optional[pd.Timestamp]) -> str:
            if ts is None or pd.isna(ts):
                return '—'
            hour = int(ts.tz_localize(None).hour)
            if 7 <= hour < 12:
                return 'London'
            if 12 <= hour < 20:
                return 'New York'
            return 'Asia'

        def _pct_to_target(row) -> Optional[float]:
            try:
                typ = str(row.get('type','')).upper()
                po = float(row.get('price_open'))
                pc = float(row.get('price_current'))
                tp = float(row.get('tp')) if 'tp' in row and row.get('tp') not in (None, '') else None
                sl = float(row.get('sl')) if 'sl' in row and row.get('sl') not in (None, '') else None
                if tp and sl:
                    if typ == 'BUY':
                        span = tp - po
                        prog = (pc - po) / span if span else 0.0
                    else:
                        span = po - tp
                        prog = (po - pc) / span if span else 0.0
                    # Clamp to [-1, 1] by mapping SL to -1, TP to +1 relative to entry
                    return max(-1.0, min(1.0, prog))
            except Exception:
                return None
            return None

        # Compact cards with hover details
        for _, row in df.iterrows():
            sym = row.get('symbol', '—')
            side = str(row.get('type',''))
            vol = row.get('volume', '')
            po = row.get('price_open', '')
            pc = row.get('price_current', '')
            pnl = float(row.get('profit', 0) or 0)
            ts = row.get('time') if 'time' in df.columns else None
            dur_txt = '—'
            if ts is not None and not pd.isna(ts):
                try:
                    mins = int((pd.Timestamp.utcnow().tz_localize(None) - ts.tz_localize(None)).total_seconds() // 60)
                    dur_txt = f"{mins}m"
                except Exception:
                    dur_txt = '—'
            sess = _session_for(ts if (ts is not None and not pd.isna(ts)) else None)
            tp = row.get('tp') if 'tp' in df.columns else None
            sl = row.get('sl') if 'sl' in df.columns else None
            pct = _pct_to_target(row)
            pct_txt = f"{int((pct or 0)*100)}%" if pct is not None else '—'
            pct_col = '#22C55E' if (pct or 0) >= 0 else '#EF4444'
            # Tooltip content
            time_disp = ts.strftime('%Y-%m-%d %H:%M') if (ts is not None and not pd.isna(ts)) else '—'
            tip = (
                f"Session: {sess}\nOpened: {time_disp}\nEntry: {po} | Now: {pc}\nSL: {sl or '—'} | TP: {tp or '—'}\nTo target: {pct_txt}"
            )
            # Translucent card row
            st.markdown(
                f"""
                <div style='padding:8px 12px;border-radius:10px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);backdrop-filter:blur(3px);margin-bottom:6px;' title="{tip}">
                  <div style='display:flex;align-items:center;justify-content:space-between;'>
                    <div style='font-weight:600;'>{sym} • {side}</div>
                    <div style='color:{'green' if pnl>0 else ('red' if pnl<0 else '#aaa')}'>{pnl:+.2f}</div>
                    <div>{vol}</div>
                    <div style='color:{pct_col}'>{pct_txt}</div>
                    <div style='opacity:0.8'>{dur_txt}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Bridge status badge (Online/Offline)
        bridge_online = False
        bridge_url_display = getattr(pulse_manager, 'mt5_url', '') or os.getenv('MT5_URL') or os.getenv('MT5_API_URL') or '—'
        try:
            if getattr(pulse_manager, 'mt5_url', None):
                r = requests.get(f"{pulse_manager.mt5_url.rstrip('/')}/health", timeout=1.0)
                bridge_online = bool(r.ok)
        except Exception:
            bridge_online = False
        st.caption(f"Bridge: {'🟢 Online' if bridge_online else '🔴 Offline'} • {bridge_url_display}")

        # Inline Protect Actions (Move SL to BE / Trail 50%)
        st.markdown("**Protect Actions — coming soon**")
        st.caption("SL → BE, trailing lock (25/50/75%), and partial closes will be enabled here.")
        # Make disabled buttons visually consistent and transparent
        st.markdown(
            """
            <style>
            div.stButton > button:disabled {
                opacity: 0.55 !important;
                background: rgba(255,255,255,0.06) !important;
                border: 1px solid rgba(255,255,255,0.18) !important;
                color: #c9c9c9 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        max_rows = min(10, len(df))
        for idx, row in df.head(max_rows).iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
            with c1:
                st.caption(f"{row.get('symbol','—')} • PnL ${float(row.get('profit',0) or 0):,.2f}")
            with c2:
                st.button(
                    "SL → BE",
                    key=f"be_{row.get('symbol','x')}_{idx}",
                    disabled=True,
                    help="Set stop-loss to entry (breakeven). Coming soon.",
                )
            with c3:
                st.button(
                    "Trail 25%",
                    key=f"trail25_{row.get('symbol','x')}_{idx}",
                    disabled=True,
                    help="Trailing stop to lock 75% of current profit. Coming soon.",
                )
            with c4:
                st.button(
                    "Trail 50%",
                    key=f"trail50_{row.get('symbol','x')}_{idx}",
                    disabled=True,
                    help="Trailing stop to lock 50% of current profit. Coming soon.",
                )
            with c5:
                st.button(
                    "Trail 75%",
                    key=f"trail75_{row.get('symbol','x')}_{idx}",
                    disabled=True,
                    help="Trailing stop to lock 25% of current profit. Coming soon.",
                )
            with c6:
                st.button("Partial 25%", key=f"partial25_{row.get('symbol','x')}_{idx}", disabled=True, help="Close 25% of position size. Coming soon.")
                st.button("Partial 50%", key=f"partial50_{row.get('symbol','x')}_{idx}", disabled=True, help="Close 50% of position size. Coming soon.")
    
    # Behavioral metrics removed per design feedback

    # Last Trade (API first, then Kafka if configured)
    st.subheader("🧾 Last Trade")
    last_trade = get_last_trade_snapshot()
    if last_trade:
        sym = last_trade.get("symbol") or last_trade.get("Symbol") or "—"
        side = last_trade.get("type") if isinstance(last_trade.get("type"), str) else {0:"BUY",1:"SELL",2:"BUY",3:"SELL"}.get(last_trade.get("type"), "—")
        pnl = float(last_trade.get("profit", 0) or 0)
        lbl = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "FLAT")
        traw = last_trade.get("time") or last_trade.get("time_close") or last_trade.get("time_done") or last_trade.get("timestamp")
        try:
            tdisp = pd.to_datetime(traw, errors="coerce").strftime("%Y-%m-%d %H:%M:%S") if traw else "—"
        except Exception:
            tdisp = "—"
        c1, c2, c3, c4 = st.columns([2,1,1,2])
        with c1:
            st.metric("Symbol / Side", f"{sym} / {side}")
        with c2:
            st.metric("Result", lbl)
        with c3:
            st.metric("PnL", f"${pnl:,.2f}")
        with c4:
            st.metric("Closed", tdisp)
    else:
        st.info("No recent trade found.")

    # Recent Trades (only)
    st.subheader("📜 Recent Trades")
    try:
        # Lazy-load recent trades to avoid slow startups
        recent_df = pd.DataFrame()
        if st.button("Load Recent Trades", key="load_recent_19") or (fast_mode and isinstance(pulse_manager._cache_get('adv19:recent_trades:20:7'), list)):
            cached_list = pulse_manager._cache_get('adv19:recent_trades:20:7')
            if isinstance(cached_list, list):
                try:
                    recent_df = pd.DataFrame(cached_list)
                except Exception:
                    recent_df = pd.DataFrame()
            if recent_df.empty:
                recent_df = pulse_manager.get_recent_trades(limit=20, days=7)
    except Exception:
        recent_df = pd.DataFrame()
    if isinstance(recent_df, pd.DataFrame) and not recent_df.empty:
        disp = recent_df.copy()
        if 'time' in disp.columns:
            try:
                disp['time'] = pd.to_datetime(disp['time']).dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass
        st.dataframe(disp, use_container_width=True)
        # Zoom into last trade details
        try:
            last_row = disp.iloc[0].to_dict()
            with st.expander('🔎 Last Trade Details', expanded=False):
                for k in ['time','symbol','type','volume','price','price_open','price_current','profit','commission','swap','comment']:
                    if k in last_row:
                        st.write(f"{k}: {last_row.get(k)}")
        except Exception:
            pass
    else:
        st.info('No recent trades available.')

    # Recent Trades and Behavioral Insights (same width)

    # Behavioral insights (below recent trades)
    st.markdown("---")
    render_behavioral_insights(pulse_manager)

    # Risk warnings (below risk metrics)
    st.markdown("---")
    st.subheader("⚠️ Risk Warnings")

    warnings = risk_data.get('warnings', [])
    
    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")
    else:
        st.success("✅ All risk parameters within limits")

    # Session trajectory (intraday equity with markers)
    st.markdown("---")
    st.subheader("📈 Session Trajectory")
    _render_session_trajectory(account_info, risk_data)

    # (Removed) duplicate performance tiles below — shown at top

    # Opportunities at the bottom
    st.markdown("---")
    render_opportunities(pulse_manager)

    # Pulse Decision Surface at the very bottom
    st.markdown("---")
    st.subheader("🎯 Pulse Decision Surface")
    fetch_cols = st.columns([1, 1, 6])
    with fetch_cols[0]:
        if st.button("Load Positions", key="load_pos_19") or (fast_mode and isinstance(pulse_manager._cache_get('adv19:positions'), list)):
            try:
                cached_pos = pulse_manager._cache_get('adv19:positions')
                positions_df = pd.DataFrame(cached_pos) if isinstance(cached_pos, list) else pulse_manager.get_positions()
            except Exception:
                positions_df = pd.DataFrame()
    with fetch_cols[1]:
        if st.button("Load Confluence", key="load_conf_19") or (fast_mode and isinstance(pulse_manager._cache_get('adv19:confluence'), dict)):
            try:
                confluence_data = pulse_manager._cache_get('adv19:confluence') or pulse_manager.get_confluence_score()
            except Exception:
                confluence_data = {}
    # Unified Whisperer Cockpit block (copied from 04-style UI)
    try:
        _render_unified_whisperer_block(account_info, risk_data)
    except Exception:
        pass

    render_pulse_tiles(pulse_manager)

    # Footer with last update time
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_gauge_chart(value: float, title: str, max_value: float = 100) -> go.Figure:
    """Create a gauge chart for risk metrics"""
    
    # Determine color based on value
    if value < 30:
        color = "green"
    elif value < 70:
        color = "yellow"
    else:
        color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': 'rgba(16,18,28,0.30)'},
                {'range': [30, 70], 'color': 'rgba(16,18,28,0.50)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

if __name__ == "__main__":
    main()
