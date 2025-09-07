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
from dashboard.components.behavioral_compass import make_behavioral_compass
from dashboard.pages.components.profit_horizon_panel import render_profit_horizon
from dashboard.pages.components.whisper_panel import render_whisper_panel
from dashboard.pages.components.whisper_timeline import render_whisper_timeline
from dashboard.pages.components.discipline_posture_panel import render_discipline_posture_panel
from dashboard.pages.components.market_header import render_market_header
from datetime import timedelta as _td
# from dashboard.components.behavioral_mirror import make_behavioral_mirror  # legacy mirror (unused)

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

# API Configuration
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")

def _pulse_url(path: str) -> str:
    """Normalize paths to pulse endpoints under /api/pulse/"""
    p = path.lstrip('/')
    if p.startswith('api/'):
        return f"{DJANGO_API_URL}/{p}"
    # Common pulse endpoints used on this page
    if p.startswith(('pulse/', 'risk/', 'score/', 'signals/')):
        # strip optional leading 'pulse/' then prefix with api/pulse
        p2 = p.split('/', 1)
        if p2 and p2[0] == 'pulse' and len(p2) > 1:
            p = p2[1]
        return f"{DJANGO_API_URL}/api/pulse/{p}"
    return f"{DJANGO_API_URL}/{p}"

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
    """Render 3 perfectly concentric, even-thickness bipolar rings.
    Outer = Patience, Middle = Discipline, Inner = Profit Efficiency.
    Rules:
      • Start at 12 o'clock, clockwise positive.
      • Arc length encodes |ratio| in that ring's color, remainder is a neutral track.
      • Ratios are clamped to [-1, 1].
    """
    import math

    # --------- helpers ---------
    def _clamp01(x: float) -> float:
        try:
            return max(0.0, min(1.0, float(x)))
        except Exception:
            return 0.0

    def _clamp11(x: float) -> float:
        try:
            return max(-1.0, min(1.0, float(x)))
        except Exception:
            return 0.0

    def _ratio_from_minutes(mins: float, target: float) -> float:
        """Map minutes-vs-target into [-1,1]; >target is good (+), <target is bad (-)."""
        try:
            if target <= 0:
                return 0.0
            return _clamp11((mins - target) / target)
        except Exception:
            return 0.0

    def _add_ring(fig, ratio: float, hole: float, thickness: float, label: str,
                  color_pos: str, color_neg: str, track: str = "rgba(255,255,255,0.08)"):
        """Overlay a single bipolar ring using a 2-slice pie [value, remainder]."""
        val = _clamp01(abs(ratio))
        color = color_pos if ratio >= 0 else color_neg
        fig.add_trace(go.Pie(
            values=[val, 1.0 - val],
            labels=[label, "_track_"],
            sort=False,
            direction="clockwise",
            rotation=0,  # 12 o'clock anchor
            hole=hole,
            textinfo="none",
            marker=dict(colors=[color, track], line=dict(color="rgba(0,0,0,0)", width=0)),
            showlegend=False,
            domain=dict(x=[0.0, 1.0], y=[0.0, 1.0])
        ))

    # --------- compute ratios from data ---------
    # Discipline (0..100), neutral ~70 → [-1,1]
    disc = _compute_discipline_today(risk_summary)
    disc_ratio = _clamp11((float(disc) - 70.0) / 30.0)

    # Patience: average minutes between trades today vs 15m target → [-1,1]
    patience_ratio = 0.0
    try:
        df = recent_df.copy()
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        dft = df[df['time'] >= pd.Timestamp.now().normalize()].sort_values('time')
        if len(dft) >= 2:
            mins = dft['time'].diff().dropna().mean().total_seconds() / 60.0
            patience_ratio = _ratio_from_minutes(mins, target=15.0)
    except Exception:
        patience_ratio = 0.0

    # Profit Efficiency: if you have a backend metric, prefer it; otherwise rough proxy
    eff_ratio = 0.0
    try:
        eff_pct = None
        # Prefer backend-provided efficiency if present
        eff_pct = float(risk_summary.get('profit_efficiency_pct')) if risk_summary.get('profit_efficiency_pct') is not None else None
        if eff_pct is None and 'profit' in recent_df.columns and len(recent_df):
            # very conservative proxy: positive P/L share
            wins = (recent_df.get('profit', 0) > 0).mean()
            eff_pct = float(wins) * 100.0
        if eff_pct is not None:
            eff_ratio = _clamp11((eff_pct - 50.0) / 50.0)
    except Exception:
        eff_ratio = 0.0

    # --------- build figure ---------
    st.markdown(f"#### {title}")
    fig = go.Figure()

    # Ring geometry (outer to inner). Same domain for perfect concentric layout.
    # thickness is implied by spaced hole values.
    OUTER_HOLE = 0.45   # Patience (outermost)
    MID_HOLE   = 0.65   # Discipline
    INNER_HOLE = 0.80   # Profit Efficiency (innermost)

    # Colors (accessible on dark bg)
    GREEN = "#22c55e"
    RED   = "#ef4444"

    _add_ring(fig, patience_ratio, OUTER_HOLE, 0.12, "Patience", GREEN, RED)
    _add_ring(fig, disc_ratio,     MID_HOLE,   0.12, "Discipline", GREEN, RED)
    _add_ring(fig, eff_ratio,      INNER_HOLE, 0.12, "Efficiency", GREEN, RED)

    # Subtle center label
    center_txt = f"<b>Patience</b> {_clamp01(abs(patience_ratio))*100:.0f}%<br>" \
                 f"<b>Discipline</b> {_clamp01(abs(disc_ratio))*100:.0f}%<br>" \
                 f"<b>Efficiency</b> {_clamp01(abs(eff_ratio))*100:.0f}%"
    fig.add_annotation(text=center_txt, x=0.5, y=0.5, showarrow=False,
                       font=dict(size=13, color="#e5e7eb"))

    # Layout polish – fully transparent bg, no margins, disable auto scaling
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)
