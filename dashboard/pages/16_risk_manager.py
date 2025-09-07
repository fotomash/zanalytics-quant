"""
Risk Management Dashboard - Production Ready
Real-time MT5 account monitoring with graceful degradation
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
import base64

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Load environment variables

load_dotenv()

# Optional baseline equity override (defaults to 200,000 if not provided)
# You can override via MT5_BASELINE_EQUITY or PULSE_BASELINE_EQUITY in .env
try:
    BASELINE_EQUITY_ENV = float(
        os.getenv("MT5_BASELINE_EQUITY", "")
        or os.getenv("PULSE_BASELINE_EQUITY", "")
        or "200000"
    )
except Exception:
    BASELINE_EQUITY_ENV = 200000.0
BASELINE_CCY = os.getenv("MT5_BASELINE_CCY", "USD")

# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse - Risk Manager",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper for background image (match Macro Intelligence page)
def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Try multiple locations for the background (match Macro & News page)
_bg_candidates = ["./pages/image_af247b.jpg", "image_af247b.jpg", "./image_af247b.jpg"]
img_base64 = None
for _p in _bg_candidates:
    try:
        img_base64 = get_base64_image(_p)
        if img_base64:
            break
    except Exception:
        continue
if not img_base64:
    img_base64 = ""

st.markdown(f"""
<style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}
    .main, .block-container {{
        background: rgba(14, 17, 23, 0.82) !important;
        border-radius: 16px;
        padding: 2.2rem 2.4rem;
        box-shadow: 0 4px 32px 0 rgba(12,10,30,0.16);
    }}
    .market-card {{
        background: rgba(26, 29, 58, 0.35);
        border-radius: 14px;
        padding: 24px 24px 14px 24px;
        border: 1.2px solid rgba(255,255,255,0.10);
        margin-bottom: 24px;
        box-shadow: 0 2px 14px 0 rgba(0,0,0,0.23);
    }}
    .pulse-tile {{
        background: rgba(26, 29, 58, 0.18);
        color: #eaeaea;
        padding: 1rem;
        border-radius: 0.75rem;
        border: 1px solid rgba(255,255,255,0.08);
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        backdrop-filter: blur(3px);
    }}
    .metric-card {{
        background: rgba(255,255,255,0.06);
        padding: 1.1rem 1.3rem;
        border-radius: 12px;
        color: #eaeaea;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 4px 16px rgba(0,0,0,0.20);
        backdrop-filter: blur(2px);
    }}
    .risk-metric {{
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }}
    .risk-high {{ background-color: #ffebee; color: #c62828; }}
    .risk-medium {{ background-color: #fff3e0; color: #ef6c00; }}
    .risk-low {{ background-color: #e8f5e9; color: #2e7d32; }}
    .spark-tile {{
        background: rgba(26, 29, 58, 0.45);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 10px 12px;
        margin: 6px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    }}
  </style>
""", unsafe_allow_html=True)

# --- Sidebar: Risk Limits (persisted) ---
with st.sidebar:
    st.header("⚠️ Risk Limits")
    st.caption("Informational sizing; they do not impose locks.")

    daily_risk_pct = st.slider(
        "Daily risk %",
        min_value=0.1, max_value=3.0, step=0.1,
        value=float(os.getenv("DAILY_RISK_PCT", "3.0")),
        help="Percent of Start-of-Day equity you're willing to risk today."
    )

    anticipated_positions = st.slider(
        "Anticipated positions today",
        min_value=1, max_value=20, step=1,
        value=int(os.getenv("ANTICIPATED_POS", "5")),
        help="How many trades you plan to take today."
    )

    st.session_state["daily_risk_pct"] = daily_risk_pct
    st.session_state["anticipated_positions"] = anticipated_positions

# ---------- Helper utilities for formatting & stats ----------
def currency_symbol(ccy: str) -> str:
    return {"GBP": "£", "USD": "$", "EUR": "€"}.get((ccy or "").upper(), "")

def fmt_ccy(amount: float, ccy: str = "USD") -> str:
    try:
        sym = currency_symbol(ccy)
        return f"{sym}{amount:,.2f}" if sym else f"{amount:,.2f} {ccy}"
    except Exception:
        return str(amount)

def start_of_day() -> datetime:
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def get_sod_equity(pulse_manager, account_info: Dict) -> float:
    """
    Compute/remember Start-of-Day equity. If Redis is available, persist the first
    equity observed today under key `equity:sod:YYYYMMDD`.
    """
    sod_key = f"equity:sod:{datetime.now().strftime('%Y%m%d')}"
    equity_now = float(account_info.get("equity", 0) or 0)
    # Prefer Redis persistence if available
    try:
        if getattr(pulse_manager, "redis_available", False) and pulse_manager.redis_client:
            val = pulse_manager.redis_client.get(sod_key)
            if val is None and equity_now > 0:
                pulse_manager.redis_client.set(sod_key, equity_now, ex=86400)
                return equity_now
            if val is not None:
                try:
                    return float(val)
                except Exception:
                    return equity_now
    except Exception:
        pass
    # Fallback: keep in session for this run
    if "sod_equity_cache" not in st.session_state:
        st.session_state["sod_equity_cache"] = equity_now
    return st.session_state["sod_equity_cache"] or equity_now

def compute_trade_stats(trades_df: pd.DataFrame) -> Dict:
    """
    Compute simple stats from trades dataframe:
    - trades_today
    - win_rate_7d (%)
    - pnl_today (sum of profit+commission+swap for today)
    """
    stats = {"trades_today": 0, "win_rate_7d": 0.0, "pnl_today": 0.0}
    if trades_df is None or trades_df.empty:
        return stats
    df = trades_df.copy()
    # Normalize time
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    else:
        df["time"] = pd.NaT
    # PnL columns
    for c in ["profit", "commission", "swap"]:
        if c not in df.columns:
            df[c] = 0.0
    df["pl_total"] = df["profit"].astype(float) + df["commission"].astype(float) + df["swap"].astype(float)
    # Today window
    sod = start_of_day()
    df_today = df[df["time"] >= sod] if df["time"].notna().any() else pd.DataFrame(columns=df.columns)
    stats["trades_today"] = int(len(df_today))
    # Win rate over last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    df_7d = df[df["time"] >= seven_days_ago] if df["time"].notna().any() else df
    total = len(df_7d)
    wins = int((df_7d["pl_total"] > 0).sum()) if total else 0
    stats["win_rate_7d"] = round((wins / total) * 100, 1) if total else 0.0
    # PnL today
    stats["pnl_today"] = float(df_today["pl_total"].sum()) if len(df_today) else 0.0
    return stats

# ------------------------------------------------------------

# ---------- Equity history helpers & micro-sparklines ----------
def _sod_key_for(dt: datetime) -> str:
    return f"equity:sod:{dt.strftime('%Y%m%d')}"

def get_sod_equity_for_date(pulse_manager, dt: datetime, fallback_equity: float = 0.0) -> Optional[float]:
    """
    Return Start-of-Day equity stored for a given date. Prefers Redis if available.
    Falls back to session cache; if missing, returns fallback_equity.
    """
    key = _sod_key_for(dt)
    try:
        if getattr(pulse_manager, "redis_available", False) and pulse_manager.redis_client:
            val = pulse_manager.redis_client.get(key)
            if val is not None:
                try:
                    return float(val)
                except Exception:
                    return fallback_equity
    except Exception:
        pass
    cache_key = f"sod_equity_cache:{key}"
    if cache_key in st.session_state:
        return float(st.session_state.get(cache_key) or 0.0)
    return fallback_equity

def get_yesterday_equities(pulse_manager, account_info: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (yesterday_open, yesterday_close).
    - yesterday_close ≈ today's SOD.
    - yesterday_open = SOD recorded for the previous day (if available).
    """
    today_sod = get_sod_equity(pulse_manager, account_info)  # today's SOD
    yesterday = datetime.now() - timedelta(days=1)
    y_open = get_sod_equity_for_date(pulse_manager, yesterday, fallback_equity=None)
    y_close = today_sod  # by definition, today's SOD equals yesterday close
    return y_open, y_close

def update_intraday_equity_series(pulse_manager, equity_now: float) -> List[Tuple[datetime, float]]:
    """
    Append current equity point to today's intraday series and return the series.
    Uses Redis list when available; otherwise, keeps a session-level list.
    """
    ts = datetime.now().isoformat()
    series_key = f"equity:intraday:{datetime.now().strftime('%Y%m%d')}"
    point = json.dumps({"ts": ts, "equity": float(equity_now or 0.0)})

    series: List[Tuple[datetime, float]] = []
    try:
        if getattr(pulse_manager, "redis_available", False) and pulse_manager.redis_client:
            # push latest point and trim to last 2880 points (~1/day @ 30s)
            pulse_manager.redis_client.rpush(series_key, point)
            pulse_manager.redis_client.ltrim(series_key, -2880, -1)
            pulse_manager.redis_client.expire(series_key, 86400)  # keep for a day
            raw = pulse_manager.redis_client.lrange(series_key, 0, -1)
            for r in raw:
                try:
                    d = json.loads(r)
                    series.append((pd.to_datetime(d.get("ts")), float(d.get("equity", 0.0))))
                except Exception:
                    continue
        else:
            # session fallback
            if series_key not in st.session_state:
                st.session_state[series_key] = []
            st.session_state[series_key].append({"ts": ts, "equity": float(equity_now or 0.0)})
            st.session_state[series_key] = st.session_state[series_key][-2000:]
            for d in st.session_state[series_key]:
                series.append((pd.to_datetime(d.get("ts")), float(d.get("equity", 0.0))))
    except Exception:
        pass
    return series

def get_7d_sod_series(pulse_manager, include_today: bool = True) -> List[Tuple[datetime, float]]:
    """
    Build a 7-day series of SOD equities from Redis/session where available.
    Optionally includes today's SOD as the last point.
    """
    series = []
    now = datetime.now()
    for i in range(1, 8):  # last 7 days (yesterday..7 days ago)
        dt = now - timedelta(days=i)
        val = get_sod_equity_for_date(pulse_manager, dt, fallback_equity=None)
        if val is not None:
            series.append((dt.replace(hour=0, minute=0, second=0, microsecond=0), float(val)))
    series = sorted(series, key=lambda x: x[0])
    if include_today:
        # add today's SOD at the end if available
        try:
            acct = st.session_state.pulse_manager.get_account_info() if 'pulse_manager' in st.session_state else {}
            today_sod = get_sod_equity(pulse_manager, acct)
            if today_sod:
                series.append((now.replace(hour=0, minute=0, second=0, microsecond=0), float(today_sod)))
        except Exception:
            pass
    return series

def make_sparkline(series: List[Tuple[datetime, float]], title: str, ccy: str = "USD", line_color: Optional[str] = None) -> go.Figure:
    """
    Create a tiny Plotly sparkline (axes hidden) using Macro & News neon style.
    If line_color is provided (e.g., "#FFD400"), it will be used regardless of delta.
    """
    if not series:
        series = [(datetime.now() - timedelta(minutes=1), 0.0), (datetime.now(), 0.0)]
    xs, ys = zip(*series)
    delta = (ys[-1] - ys[0]) if ys else 0.0
    color = line_color or ("#00FFC6" if delta >= 0 else "#FF4B6E")  # Neon default
    last_val = ys[-1] if ys else 0.0

    fig = go.Figure(
        data=[
            go.Scatter(
                x=list(xs),
                y=list(ys),
                mode="lines",
                line=dict(width=3, color=color),
                hoverinfo="skip",
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        height=120,
        margin=dict(l=10, r=10, t=28, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        title=dict(
            text=title,
            x=0.02, y=0.95,
            xanchor="left",
            yanchor="top",
            font=dict(size=13, color="#eaeaea", family="Arial, sans-serif")
        ),
    )
    # Value annotation (top-right)
    fig.add_annotation(
        text=f"{fmt_ccy(last_val, ccy)}",
        xref="paper", yref="paper",
        x=0.98, y=0.95,
        xanchor="right", yanchor="top",
        showarrow=False,
        font=dict(size=13, color="#eaeaea")
    )
    return fig


# --- Allowed loss helpers (daily & per-trade), and top stats UI ---
def calc_allowed_losses(sod_equity: float, daily_risk_pct: float, anticipated_positions: int) -> dict:
    """
    Given SOD equity and user risk settings:
      - daily_risk_pct: 0.1 .. 3.0 (% of SOD)
      - anticipated_positions: integer >= 1
    return dict with absolute amounts and per-trade cap.
    """
    daily_cap = float(max(daily_risk_pct, 0.0)) * 0.01 * float(sod_equity or 0.0)
    positions = max(int(anticipated_positions or 1), 1)
    per_trade_cap = daily_cap / positions if positions > 0 else 0.0
    return {
        "daily_cap": daily_cap,
        "per_trade_cap": per_trade_cap,
        "positions": positions,
    }

def render_top_account_statistics(pulse_manager):
    """Top section: Account Statistics + micro sparklines using Macro/News neon style."""
    # Account info (real bridge preferred)
    acct = pulse_manager.get_account_info() if pulse_manager else {}
    ccy = acct.get("currency", BASELINE_CCY)
    equity_now = float(acct.get("equity", 0.0) or 0.0)
    balance_now = float(acct.get("balance", 0.0) or 0.0)

    # Baselines & SOD
    baseline_equity = get_baseline_equity(pulse_manager, acct)  # default 200,000 from env
    sod_equity = get_sod_equity(pulse_manager, acct)

    # Trades (for PnL today / win-rate)
    try:
        recent = pulse_manager.get_recent_trades(limit=250, days=7)
    except Exception:
        recent = None
    stats = compute_trade_stats(recent if isinstance(recent, pd.DataFrame) else pd.DataFrame())
    pnl_today = float(stats.get("pnl_today", 0.0))

    # User risk knobs from sidebar
    daily_risk_pct = float(st.session_state.get("daily_risk_pct", 3.0))
    anticipated_positions = int(st.session_state.get("anticipated_positions", 5))
    loss_caps = calc_allowed_losses(sod_equity, daily_risk_pct, anticipated_positions)

    # Intraday equity series (spark) + yesterday opens/close (sparks)
    intraday_series = update_intraday_equity_series(pulse_manager, equity_now)
    y_open, y_close = get_yesterday_equities(pulse_manager, acct)
    series_7d = get_7d_sod_series(pulse_manager, include_today=True)

    # Real account badge: show account number and broker if available
    login = acct.get("login")
    broker = acct.get("server") or acct.get("company")
    if login:
        st.markdown(
            f'<div class="market-card" style="text-align:center;">'
            f'<span style="background:#99ffd0;color:#181818;padding:8px 14px;border-radius:12px;font-weight:800;">'
            f'Account {login} • {broker or "—"}'
            f'</span></div>',
            unsafe_allow_html=True
        )

    st.markdown("### Equity Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Previous Session Close Equity", fmt_ccy(y_close or sod_equity, ccy))
    with c2:
        st.metric("Today Opening Equity", fmt_ccy(sod_equity, ccy), delta=fmt_ccy(equity_now - sod_equity, ccy))
    with c3:
        st.metric("Current Equity", fmt_ccy(equity_now, ccy), delta=f"{((equity_now / (sod_equity or equity_now) - 1) * 100):.2f}% vs. SOD" if sod_equity else "—")
    with c4:
        st.metric("Max Allowed Loss Today", fmt_ccy(loss_caps['daily_cap'], ccy), delta=f"{daily_risk_pct:.1f}% of SOD")
    with c5:
        st.metric("Max Loss / Trade", fmt_ccy(loss_caps['per_trade_cap'], ccy), delta=f"{loss_caps['positions']} anticipated")
    st.caption(f"Starting Equity Baseline: {fmt_ccy(baseline_equity, ccy)}")

    # Allowed loss tiles
    t0, t1, t2 = st.columns(3)
    with t0:
        st.markdown("**Max Daily Loss %**")
        st.markdown(f"<div class='metric-card'>{daily_risk_pct:.1f}%</div>", unsafe_allow_html=True)
    with t1:
        st.markdown("**Max Allowed Loss Today**")
        st.markdown(f"<div class='metric-card'>{fmt_ccy(loss_caps['daily_cap'], ccy)}</div>", unsafe_allow_html=True)
    with t2:
        st.markdown(f"**Max Loss Per Trade** (/{loss_caps['positions']} anticipated)")
        st.markdown(f"<div class='metric-card'>{fmt_ccy(loss_caps['per_trade_cap'], ccy)}</div>", unsafe_allow_html=True)

    # Micro charts row – same transparent style as Macro News tiles
    st.markdown("---")
    st.subheader("Equity Micro Charts")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.plotly_chart(make_sparkline(intraday_series, "Intraday Equity", ccy, line_color="#00FFC6"), use_container_width=True, config={"displayModeBar": False})
    with s2:
        # yesterday open/close spark (if available)
        y_series = []
        if y_open is not None:
            y_series.append((datetime.now() - timedelta(days=1), float(y_open)))
        if y_close is not None:
            y_series.append((datetime.now(), float(y_close)))
        st.plotly_chart(make_sparkline(y_series, "Previous Session Open→Close", ccy, line_color="#FFD400"), use_container_width=True, config={"displayModeBar": False})
    with s3:
        st.plotly_chart(make_sparkline(series_7d, "7d SOD Trail", ccy, line_color="#9b59b6"), use_container_width=True, config={"displayModeBar": False})

def render_recent_trades_section(pulse_manager, limit: int = 10):
    st.markdown("---")
    st.subheader("📜 Recent Trades")
    try:
        df = pulse_manager.get_recent_trades(limit=limit, days=7)
    except Exception:
        df = pd.DataFrame()
    if isinstance(df, pd.DataFrame) and not df.empty:
        acct = pulse_manager.get_account_info() if pulse_manager else {}
        ccy = acct.get("currency", BASELINE_CCY)
        show = format_trades_for_display(df, ccy)
        if "time" in show.columns:
            try:
                show["time"] = pd.to_datetime(show["time"]).dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        st.dataframe(show, use_container_width=True)
    else:
        st.info("No recent trades returned by the bridge.")


# ------------------- Baseline equity and trade display helpers -------------------
def get_baseline_equity(pulse_manager, account_info: Dict) -> float:
    """
    Baseline (starting) equity:
      1) Env var MT5_BASELINE_EQUITY / PULSE_BASELINE_EQUITY if set (default 200,000),
      2) else Redis key 'equity:baseline' (seeded from broker balance),
      3) else current balance/equity.
    """
    if BASELINE_EQUITY_ENV:
        return float(BASELINE_EQUITY_ENV)
    try:
        if getattr(pulse_manager, "redis_available", False) and pulse_manager.redis_client:
            v = pulse_manager.redis_client.get("equity:baseline")
            if v is not None:
                return float(v)
            seed = account_info.get("balance") or account_info.get("equity")
            if seed:
                pulse_manager.redis_client.set("equity:baseline", float(seed))
                return float(seed)
    except Exception:
        pass
    return float(account_info.get("balance") or account_info.get("equity") or 0.0)

def format_trades_for_display(df: pd.DataFrame, ccy: str = "USD") -> pd.DataFrame:
    """
    Clean recent trades for UI display: hide ticket/order IDs, keep human fields only.
    Columns kept (when available): time, symbol, type, volume, price_open, price_close, profit, comment.
    Adds 'profit_ccy' formatted column.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    keep = [c for c in ["time", "symbol", "type", "volume", "price_open", "price_close", "profit", "comment"] if c in df.columns]
    out = df[keep].copy()
    if "type" in out.columns:
        out["type"] = out["type"].replace({0: "BUY", 1: "SELL", 2: "BUY", 3: "SELL"})
    if "profit" in out.columns:
        out["profit_ccy"] = out["profit"].astype(float).apply(lambda x: fmt_ccy(x, ccy))
    if "time" in out.columns:
        try:
            out = out.sort_values("time", ascending=False)
        except Exception:
            pass
    return out

# API Configuration
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")

def safe_api_call(method: str, path: str, payload: Dict = None, timeout: float = 2.0) -> Dict:
    """Safe API call with error handling and fallbacks"""
    try:
        url = f"{DJANGO_API_URL}/{path.lstrip('/')}"
        
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload or {}, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"error": "API timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "API connection failed"}
    except Exception as e:
        return {"error": str(e)}

class PulseRiskManager:
    """Enhanced Risk Manager with Pulse Integration and Error Handling"""

    def __init__(self):
        # Get credentials from environment (no defaults to real values)
        self.mt5_login = os.getenv('MT5_LOGIN')
        self.mt5_password = os.getenv('MT5_PASSWORD')
        self.mt5_server = os.getenv('MT5_SERVER')
        
        # Initialize connections
        self.connected = False
        self.mt5_available = MT5_AVAILABLE

        # Optional HTTP MT5 bridge (same one used by page 17)
        self.mt5_url = os.getenv("MT5_URL", "http://mt5:5001")
        # Annotate source so the UI can state "real MetaTrader account via HTTP bridge"
        self.using_http_bridge = True if self.mt5_url else False
        # status bookkeeping for bottom-of-page status panel (no top-level warnings)
        self.status_messages = []
        self.bridge_available = False
        
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
        """Connect to MT5 with proper error handling"""
        if not self.mt5_available:
            self.status_messages.append("MT5 module not available → using HTTP bridge / mock mode")
            return False
        
        if not all([self.mt5_login, self.mt5_password, self.mt5_server]):
            self.status_messages.append("MT5 credentials not configured → using HTTP bridge / mock mode")
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

    def get_account_info(self) -> Dict:
        """Get account information. No mocks; only real sources."""
        # Try HTTP MT5 bridge first
        if self.mt5_url:
            try:
                r = requests.get(f"{self.mt5_url}/account_info", timeout=2.0)
                if r.ok:
                    data = r.json() or {}
                    if isinstance(data, dict) and data:
                        self.bridge_available = True
                        return data
                else:
                    self.status_messages.append(f"HTTP bridge /account_info returned {r.status_code}")
            except Exception as e:
                self.status_messages.append(f"HTTP bridge error: {e}")
        # Try native MT5 if available and credentials are set
        if self.mt5_available and all([self.mt5_login, self.mt5_password, self.mt5_server]):
            try:
                if not self.connected:
                    if mt5.initialize() and mt5.login(login=int(self.mt5_login), password=self.mt5_password, server=self.mt5_server):
                        self.connected = True
                if self.connected:
                    ai = mt5.account_info()
                    if ai:
                        return {
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
            except Exception as e:
                self.status_messages.append(f"MT5 native error: {e}")
        # No data available
        return {}

    def get_positions(self) -> pd.DataFrame:
        """Get all open positions with error handling"""
        # Try HTTP MT5 bridge if available
        try:
            if self.mt5_url:
                r = requests.get(f"{self.mt5_url}/positions_get", timeout=2.0)
                if r.ok:
                    self.bridge_available = True
                    data = r.json() or []
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                        # Normalize time columns if present
                        for col in ("time", "time_update"):
                            if col in df.columns:
                                try:
                                    df[col] = pd.to_datetime(df[col])
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
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df['time_update'] = pd.to_datetime(df['time_update'], unit='s')
                    return df
        except Exception:
            pass
        return pd.DataFrame()
st.markdown("""
<style>
.psychology-insight {
    background: rgba(255,255,255,0.08) !important;
    border-left: 3px solid rgba(153,255,208,0.85) !important;
    padding: 0.9rem 1rem !important;
    margin: 0.75rem 0 !important;
    border-radius: 0 10px 10px 0 !important;
    color: #eaeaea !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.25) !important;
    backdrop-filter: blur(3px) !important;
}
div[data-testid="stExpander"] > details {
    background: rgba(26, 29, 58, 0.35) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25) !important;
}
div[data-testid="stExpander"] summary {
    color: #eaeaea !important;
}
</style>
""", unsafe_allow_html=True)
def make_drawdown_bar(used_frac: float, dd_pct: float, cap_pct: float) -> go.Figure:
    """
    Horizontal bar showing today's drawdown vs. daily cap.
    used_frac: 0..1 (portion of cap used)
    dd_pct: today's loss as % of SoD (positive means loss)
    cap_pct: allowed daily risk % of SoD
    """
    u = max(0.0, min(1.0, float(used_frac or 0.0)))
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[u * 100],
        y=[""],
        orientation="h",
        marker=dict(color="rgba(239,68,68,0.85)"),  # red-ish
        hovertemplate="Used: %{x:.1f}% of cap<extra></extra>",
        name="Used"
    ))
    fig.add_trace(go.Bar(
        x=[(1.0 - u) * 100],
        y=[""],
        orientation="h",
        marker=dict(color="rgba(16,185,129,0.45)"),  # green-ish translucent
        hovertemplate="Remaining: %{x:.1f}% of cap<extra></extra>",
        name="Remaining"
    ))
    fig.update_layout(
        barmode="stack",
        height=70,
        margin=dict(l=6, r=6, t=8, b=6),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            range=[0, 100],
            showgrid=False,
            zeroline=False,
            visible=False
        ),
        yaxis=dict(visible=False),
        title=dict(text=f"Session Drawdown {dd_pct:.2f}%  •  Cap {cap_pct:.2f}%", x=0.0, y=0.98, font=dict(size=12))
    )
    return fig

    

    def get_mt5_data(self, endpoint: str) -> Optional[Dict]:
        """Query the MT5 HTTP bridge (same style as page 17)."""
        try:
            r = requests.get(f"{self.mt5_url}/{endpoint.lstrip('/')}", timeout=2.0)
            if r.ok:
                return r.json()
        except Exception:
            pass
        return None

    def get_recent_trades(self, limit: int = 10, days: int = 7) -> pd.DataFrame:
        """
        Try MT5 HTTP bridge endpoints for recent trades; fall back to empty DF.
        Expected endpoints:
          - history_deals_get?days={days}&limit={limit}
          - history_orders_get?days={days}&limit={limit}
          - history_deals_get?from=ISO&to=ISO&limit={limit}
        """
        candidates = [
            f"history_deals_get?days={days}&limit={limit}",
            f"history_orders_get?days={days}&limit={limit}",
            f"history_deals_get?from={(datetime.now()-timedelta(days=days)).isoformat()}&to={datetime.now().isoformat()}&limit={limit}",
        ]
        for ep in candidates:
            data = self.get_mt5_data(ep)
            if data and isinstance(data, list):
                df = pd.DataFrame(data)
                # normalize time column
                time_cols = [c for c in ["time", "time_msc", "time_done", "time_close"] if c in df.columns]
                if time_cols:
                    col = time_cols[0]
                    try:
                        df["time"] = pd.to_datetime(df[col], unit="s", errors="coerce")
                    except Exception:
                        df["time"] = pd.to_datetime(df[col], errors="coerce")
                elif "timestamp" in df.columns:
                    df["time"] = pd.to_datetime(df["timestamp"], errors="coerce")
                if "type" in df.columns:
                    df["type"] = df["type"].replace({0: "BUY", 1: "SELL", 2: "BUY", 3: "SELL"})
                cols = [c for c in ["time","ticket","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in df.columns]
                if "time" in cols:
                    df = df.sort_values("time", ascending=False)
                return df[cols].head(limit) if cols else df.head(limit)
        return pd.DataFrame()

    def get_confluence_score(self) -> Dict:
        """Get confluence score from Pulse API. No mocks."""
        result = safe_api_call("POST", "score/peek", {})
        return result if isinstance(result, dict) else {}

    def get_risk_summary(self) -> Dict:
        """Get risk summary from Pulse API. No mocks."""
        result = safe_api_call("GET", "risk/summary")
        return result if isinstance(result, dict) else {}

    def get_top_opportunities(self, n: int = 3) -> List[Dict]:
        """Get top trading opportunities. No mocks."""
        result = safe_api_call("GET", f"signals/top?n={n}")
        return result if isinstance(result, list) else []

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
                {'range': [0, 30], 'color': "lightgray"},
                {'range': [30, 70], 'color': "gray"}
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

def render_pulse_tiles(pulse_manager: PulseRiskManager):
    """Render Pulse-specific tiles with error handling"""
    st.subheader("🎯 Pulse Decision Surface")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Confluence Score Tile
    with col1:
        confluence_data = pulse_manager.get_confluence_score()
        score = confluence_data.get("score", 0)
        grade = confluence_data.get("grade", "Unknown")
        
        st.markdown(f"""
        <div class="pulse-tile">
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
        bias = "Bull" if score > 60 else "Bear" if score < 40 else "Neutral"
        bias_color = "🟢" if bias == "Bull" else "🔴" if bias == "Bear" else "🟡"
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Market Bias</h4>
            <h2>{bias_color} {bias}</h2>
            <p>Confidence: {score}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Risk Remaining Tile
    with col3:
        try:
            if hasattr(pulse_manager, "get_risk_summary"):
                risk_data = pulse_manager.get_risk_summary()
            else:
                rd = safe_api_call("GET", "risk/summary")
                risk_data = rd if isinstance(rd, dict) else {}
        except Exception:
            risk_data = {}
        risk_remaining = risk_data.get("risk_left", 0)
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Risk Remaining</h4>
            <h2>{risk_remaining:.1f}%</h2>
            <p>Daily Budget</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Suggested R:R Tile
    with col4:
        suggested_rr = 2.0 if score > 70 else 1.5 if score > 50 else 1.2
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Suggested R:R</h4>
            <h2>{suggested_rr}:1</h2>
            <p>Based on Score</p>
        </div>
        """, unsafe_allow_html=True)

def render_opportunities(pulse_manager: PulseRiskManager):
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

def render_behavioral_insights(pulse_manager: PulseRiskManager):
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

def main():
    """Main dashboard function with comprehensive error handling"""
    
    st.title("🎯 Zanalytics Pulse - Risk Management Dashboard")
    st.markdown("### Behavioral-First Risk Management with Real-Time MT5 Integration")

    # Initialize Pulse Risk Manager (ensure this page's manager, not advanced)
    if 'pulse_manager' not in st.session_state or not isinstance(st.session_state.pulse_manager, PulseRiskManager):
        st.session_state.pulse_manager = PulseRiskManager()

    pulse_manager = st.session_state.pulse_manager

    # Data-source banner: account number and broker if available
    acct_info_banner = pulse_manager.get_account_info() if pulse_manager else {}
    login_banner = acct_info_banner.get("login")
    broker_banner = acct_info_banner.get("server") or acct_info_banner.get("company")
    if login_banner:
        st.markdown(
            f'''
            <div class="market-card" style="text-align:center;">
                <span style="background: #99ffd0; color:#181818; padding:8px 14px; border-radius:12px; font-weight:800;">
                    Account {login_banner} • {broker_banner or '—'}
                </span>
            </div>
            ''',
            unsafe_allow_html=True
        )

    # System health status
    health_data = safe_api_call("GET", "pulse/health")
    if "error" not in health_data:
        status = health_data.get("status", "unknown")
        lag = health_data.get("lag_ms", "—")
        st.caption(f"System Status: {status} | Lag: {lag}ms | Last Update: {datetime.now().strftime('%H:%M:%S')}")

        # -------- TOP: Account Statistics (Balance/Equity first) --------
        acct = pulse_manager.get_account_info()
        ccy = acct.get("currency") or BASELINE_CCY

        # SOD & Baseline (baseline defaults to 200,000 via env)
        baseline_equity = get_baseline_equity(pulse_manager, acct)
        sod_equity = get_sod_equity(pulse_manager, acct) or float(acct.get("equity") or 0.0)

        # Risk limit inputs (from sidebar)
        daily_risk_pct = float(st.session_state.get("daily_risk_pct", float(os.getenv("DAILY_RISK_PCT","3.0"))))
        anticipated_positions = int(st.session_state.get("anticipated_positions", int(os.getenv("ANTICIPATED_POS","5"))))
        limits = calc_allowed_losses(sod_equity, daily_risk_pct, anticipated_positions)
        st.session_state["risk_limits:max_loss_today"] = limits["daily_cap"]
        st.session_state["risk_limits:max_loss_per_trade"] = limits["per_trade_cap"]

        # Equity series for tiles
        eq_now = float(acct.get("equity") or 0.0)
        series_intraday = update_intraday_equity_series(pulse_manager, eq_now)
        y_open, y_close = get_yesterday_equities(pulse_manager, acct)
        series_7d = get_7d_sod_series(pulse_manager, include_today=True)

        # Today's P&L & quick stats from trades
        trades_df = pulse_manager.get_recent_trades(limit=250, days=1)
        trade_stats = compute_trade_stats(trades_df)

        st.markdown("## 📊 Equity Summary")
        c1, c2, c3, c4, c5 = st.columns(5)
        prev_close = y_close or sod_equity
        with c1:
            st.metric("Previous Session Close Equity", fmt_ccy(prev_close, ccy))
        with c2:
            st.metric("Today Opening Equity", fmt_ccy(sod_equity, ccy), delta=fmt_ccy(eq_now - sod_equity, ccy))
        with c3:
            st.metric("Current Equity", fmt_ccy(eq_now, ccy), delta=f"{((eq_now / (sod_equity or eq_now) - 1) * 100):.2f}% vs. SOD" if sod_equity else "—")
        with c4:
            st.metric("Max Allowed Loss Today", fmt_ccy(limits["daily_cap"], ccy), delta=f"{daily_risk_pct:.1f}% of SOD")
        with c5:
            st.metric("Max Loss / Trade", fmt_ccy(limits["per_trade_cap"], ccy), delta=f"{anticipated_positions} anticipated")
        st.caption(f"Starting Equity Baseline: {fmt_ccy(baseline_equity, ccy)}")

        # Session Drawdown vs Daily Cap  +  Per-Trade Risk Suggestion
        dd_pct = compute_daily_loss_pct(pulse_manager, acct)
        used_frac = min(dd_pct / max(daily_risk_pct, 1e-6), 1.0) if daily_risk_pct > 0 else 0.0
        dcol1, dcol2 = st.columns([2, 1])
        with dcol1:
            st.plotly_chart(
                make_drawdown_bar(used_frac, dd_pct, daily_risk_pct),
                use_container_width=True,
                config={"displayModeBar": False}
            )
        with dcol2:
            try:
                _peek = pulse_manager.get_confluence_score()
                _score = float(_peek.get("score", 0) or 0.0)
            except Exception:
                _score = 0.0
            _per_trade_pct = (daily_risk_pct / max(anticipated_positions, 1))
            _adj_pct = _per_trade_pct * max(min(_score, 100.0), 0.0) / 100.0
            _adj_amt = (sod_equity or 0.0) * _adj_pct / 100.0
            st.metric("Per-Trade Risk Suggestion", f"{_adj_pct:.2f}%", delta=f"{fmt_ccy(_adj_amt, ccy)}  at score {_score:.0f}")

        # Tiny transparent sparklines (DXY-style)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.plotly_chart(make_sparkline(series_intraday, "Equity (intraday)", ccy=ccy, line_color="#FFD400"),
                            use_container_width=True, config={"displayModeBar": False})
        with m2:
            if y_open is not None:
                st.plotly_chart(make_sparkline(
                    [(datetime.now()-timedelta(days=1), y_open), (datetime.now(), y_close or sod_equity)],
                    "Previous Session Open→Close", ccy=ccy, line_color="#FFD400"),
                    use_container_width=True, config={"displayModeBar": False}
                )
            else:
                st.plotly_chart(make_sparkline([], "Previous Session Open→Close", ccy=ccy, line_color="#FFD400"),
                                use_container_width=True, config={"displayModeBar": False})
        with m3:
            st.plotly_chart(make_sparkline(series_7d, "Start-of-Day Equity (7d)", ccy=ccy, line_color="#FFD400"),
                            use_container_width=True, config={"displayModeBar": False})

        st.divider()

        # Ensure Pulse tiles render below account stats
        try:
            render_pulse_tiles(pulse_manager)
            st.divider()
        except Exception as _e:
            pass

        # Recent trades table (no ticket/order ids)
        st.subheader("📋 Recent Trades")
        trades_df = pulse_manager.get_recent_trades(limit=25, days=7)
        if trades_df is not None and not trades_df.empty:
            display = format_trades_for_display(trades_df, ccy=ccy)
            st.dataframe(display, use_container_width=True)
        else:
            st.info("No recent trades available")
        st.caption(f"System Status: offline | Last Update: {datetime.now().strftime('%H:%M:%S')}")

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Controls")

        # Connection status
        if st.button("🔌 Connect to MT5"):
            if pulse_manager.connect():
                st.success("✅ Connected to MT5")
            else:
                st.warning("⚠️ Running in mock mode")

        # Refresh settings
        auto_refresh = st.checkbox("Auto Refresh", value=False)
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 60, 5)

        # Risk limits
        st.header("⚠️ Risk Limits")
        daily_loss_limit = st.slider("Daily Risk Budget (%)", 0.1, 3.0, 3.0, step=0.1)
        anticipated_positions = st.slider("Anticipated Positions Today", 1, 12, 4)
        max_positions = st.number_input("Max Open Positions", 1, 20, 5)
        per_trade_risk = daily_loss_limit / anticipated_positions
        st.caption(f"Suggested per-trade risk: {per_trade_risk:.2f}% of equity")

        # Display settings
        st.header("📊 Display Settings")
        show_pulse_tiles = st.checkbox("Show Pulse Tiles", value=True)
        show_positions = st.checkbox("Show Open Positions", value=True)
        show_opportunities = st.checkbox("Show Opportunities", value=True)
        show_behavioral = st.checkbox("Show Behavioral Insights", value=True)

    # Auto-refresh logic
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

    # Get account information and risk status (robust to missing methods)
    try:
        account_info = pulse_manager.get_account_info()
    except Exception as e:
        st.error(f"Error loading account: {e}")
        account_info = {}
    try:
        positions_df = pulse_manager.get_positions() if hasattr(pulse_manager, 'get_positions') else pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading positions: {e}")
        positions_df = pd.DataFrame()
    try:
        if hasattr(pulse_manager, 'get_risk_summary'):
            risk_data = pulse_manager.get_risk_summary()
        else:
            rd = safe_api_call("GET", "risk/summary")
            risk_data = rd if isinstance(rd, dict) else {}
    except Exception as e:
        st.error(f"Error loading risk summary: {e}")
        risk_data = {}

    # --- Account stats & history snapshot ---
    try:
        if hasattr(pulse_manager, 'get_recent_trades'):
            recent_trades_df = pulse_manager.get_recent_trades(limit=50, days=7)
        else:
            recent_trades_df = fetch_recent_trades_fallback(pulse_manager, limit=50, days=7)
    except Exception:
        recent_trades_df = fetch_recent_trades_fallback(pulse_manager, limit=50, days=7)
    sod_equity = get_sod_equity(pulse_manager, account_info)
    baseline_equity = float(os.getenv("STARTING_EQUITY", "200000") or 200000)
    acct_ccy = account_info.get("currency", "USD")
    max_allowed_loss_amt = (sod_equity or 0) * (daily_loss_limit / 100.0)
    trade_stats = compute_trade_stats(recent_trades_df)

    # --- Equity microcharts (Yesterday / Today / 7d SOD) -------------------
    y_open, y_close = get_yesterday_equities(pulse_manager, account_info)
    intraday_series = update_intraday_equity_series(pulse_manager, float(account_info.get("equity", 0.0) or 0.0))
    sod7d_series = get_7d_sod_series(pulse_manager, include_today=True)

    # Build tiny sequences
    yesterday_series = []
    if y_open is not None and y_close is not None:
        # two-point sparkline: yesterday open -> yesterday close (today's SOD)
        yesterday_series = [
            (datetime.now() - timedelta(days=1), float(y_open)),
            (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), float(y_close)),
        ]
    elif y_close is not None:
        yesterday_series = [
            (datetime.now() - timedelta(days=1), float(y_close)),
            (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), float(y_close)),
        ]

    st.markdown("#### 📈 Equity Summary")
    col_eq1, col_eq2, col_eq3 = st.columns(3)

    with col_eq1:
        fig = make_sparkline(yesterday_series, "Yesterday (Open → Close)", acct_ccy)
        st.plotly_chart(fig, use_container_width=True)
        if y_open is not None and y_close is not None:
            delta = y_close - y_open
            st.caption(f"Δ {fmt_ccy(delta, acct_ccy)}  |  Open {fmt_ccy(y_open, acct_ccy)} → Close {fmt_ccy(y_close, acct_ccy)}")

    with col_eq2:
        # Today sparkline: SoD → Now (intraday)
        today_series = []
        if intraday_series:
            # ensure first point starts at SoD equity for clarity
            if sod_equity:
                today_series = [(intraday_series[0][0].replace(hour=0, minute=0, second=0, microsecond=0), float(sod_equity))] + intraday_series[-120:]
            else:
                today_series = intraday_series[-120:]
        fig = make_sparkline(today_series, "Today (SoD → Now)", acct_ccy)
        st.plotly_chart(fig, use_container_width=True)
        if sod_equity:
            delta_today = float(account_info.get("equity", 0.0) or 0.0) - float(sod_equity or 0.0)
            st.caption(f"Δ {fmt_ccy(delta_today, acct_ccy)}  |  SoD {fmt_ccy(sod_equity, acct_ccy)}")

    with col_eq3:
        fig = make_sparkline(sod7d_series, "Start-of-Day Equity (7d)", acct_ccy)
        st.plotly_chart(fig, use_container_width=True)
        if len(sod7d_series) >= 2:
            st.caption(f"{sod7d_series[0][0].strftime('%d %b')} → {sod7d_series[-1][0].strftime('%d %b')}")

    # Pulse Decision Surface
    if show_pulse_tiles:
        render_pulse_tiles(pulse_manager)
        st.divider()

    # --- Key Risk Stats (informational, non-enforcing) ---
    st.subheader("📊 Key Risk Stats")
    colA, colB, colC, colD, colE = st.columns(5)
    prev_close_disp = y_close or sod_equity
    with colA:
        st.metric("Previous Session Close Equity", fmt_ccy(prev_close_disp, acct_ccy))
    with colB:
        st.metric("Start-of-Day Equity", fmt_ccy(sod_equity, acct_ccy))
    with colC:
        st.metric("Today's P&L", fmt_ccy(trade_stats["pnl_today"], acct_ccy))
    with colD:
        st.metric("Max Allowed Loss (info)", fmt_ccy(max_allowed_loss_amt, acct_ccy), help="Daily Risk Budget × Start-of-Day equity. Informational only.")
    with colE:
        st.metric("Win Rate (7D)", f"{trade_stats['win_rate_7d']:.1f}%")
    st.caption(f"Starting Equity Baseline: {fmt_ccy(baseline_equity, acct_ccy)}  •  Derived from your MetaTrader bridge when available. Informational; not enforced.")
    st.markdown("---")

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "💰 Balance",
            f"${account_info.get('balance', 0):,.2f}",
            f"${account_info.get('profit', 0):,.2f}"
        )

    with col2:
        equity = account_info.get('equity', 0)
        balance = account_info.get('balance', 1)
        equity_change = ((equity / balance - 1) * 100) if balance > 0 else 0
        
        st.metric(
            "📊 Equity",
            f"${equity:,.2f}",
            f"{equity_change:.2f}%"
        )

    with col3:
        margin_level = account_info.get('margin_level', 0)
        st.metric(
            "🎯 Margin Level",
            f"{margin_level:,.2f}%",
            "Safe" if margin_level > 200 else "Warning"
        )

    with col4:
        risk_used = risk_data.get('daily_risk_used', 0)
        st.metric(
            "📈 Risk Used",
            f"{risk_used:.1f}%",
            f"Phase: {risk_data.get('status', 'Unknown')}"
        )

    with col5:
        st.metric(
            "🔢 Open Positions",
            len(positions_df),
            f"Max: {max_positions}"
        )

    # Risk gauges
    st.markdown("---")
    st.subheader("🎯 Risk Metrics")

    gauge_col1, gauge_col2, gauge_col3, gauge_col4 = st.columns(4)

    with gauge_col1:
        fig = create_gauge_chart(risk_data.get('daily_risk_used', 0), "Daily Risk Used (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col2:
        drawdown = abs(account_info.get('profit', 0)) / account_info.get('balance', 1) * 100 if account_info.get('balance', 0) > 0 else 0
        fig = create_gauge_chart(drawdown, "Current Drawdown (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col3:
        trades_used = risk_data.get('trades_used', 0)
        max_trades = risk_data.get('max_trades', 5)
        trade_usage = (trades_used / max_trades) * 100 if max_trades > 0 else 0
        fig = create_gauge_chart(trade_usage, "Trade Limit Usage (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col4:
        overall_risk = min(risk_data.get('daily_risk_used', 0) + drawdown, 100)
        fig = create_gauge_chart(overall_risk, "Overall Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        # Trading opportunities
        if show_opportunities:
            render_opportunities(pulse_manager)

        # Open positions table
        if show_positions and not positions_df.empty:
            st.subheader("📋 Open Positions")

            # Format positions dataframe
            display_cols = ['symbol', 'type', 'volume', 'price_open',
                          'price_current', 'profit', 'time']
            positions_display = positions_df[display_cols].copy()
            positions_display['type'] = positions_display['type'].map({0: 'BUY', 1: 'SELL'})

            # Color code profit/loss
            def color_profit(val):
                color = 'green' if val > 0 else 'red' if val < 0 else 'black'
                return f'color: {color}'

            styled_positions = positions_display.style.applymap(
                color_profit, subset=['profit']
            )

            st.dataframe(styled_positions, use_container_width=True)

            # Recent Trades (from MT5 bridge)
            st.markdown("---")
            st.subheader("📜 Recent Trades")
            recent_trades = recent_trades_df.copy() if isinstance(recent_trades_df, pd.DataFrame) else pd.DataFrame()
            if isinstance(recent_trades, pd.DataFrame) and not recent_trades.empty:
                display_cols = [c for c in ["time","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in recent_trades.columns]
                df_show = recent_trades[display_cols].copy() if display_cols else recent_trades.copy()
                if "time" in df_show.columns:
                    df_show["time"] = pd.to_datetime(df_show["time"]).dt.strftime("%Y-%m-%d %H:%M")
                # Render as compact cards with Analyze button
                for idx, row in df_show.head(10).iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                        with c1:
                            st.write(f"**{row.get('symbol','')}**  •  {row.get('type','')}  •  {row.get('time','')}")
                            vol_txt = f"{row.get('volume','')}" if 'volume' in df_show.columns else ""
                            st.caption(f"Volume: {vol_txt}")
                        with c2:
                            po = row.get('price_open', None)
                            pc = row.get('price_current', row.get('price', None))
                            st.write(f"Open: {po if po is not None else '—'}")
                            st.write(f"Close: {pc if pc is not None else '—'}")
                        with c3:
                            pl = float(row.get('profit', 0) or 0) + float(row.get('commission', 0) or 0) + float(row.get('swap', 0) or 0)
                            st.write(f"PnL: {fmt_ccy(pl, acct_ccy)}")
                        with c4:
                            btn_key = f"analyze_trade_{idx}"
                            if st.button("🔎 Analyze", key=btn_key):
                                # Ask Pulse for a quick read
                                peek = safe_api_call("POST", "score/peek", {"symbol": row.get("symbol")})
                                score = peek.get("score", 0) if isinstance(peek, dict) else 0
                                rc = safe_api_call("POST", "risk/check", {"symbol": row.get("symbol"), "confluence_score": score, "risk_reward": 2.0})
                                st.session_state[f"analysis_{idx}"] = {"peek": peek, "risk": rc}
                            # Show analysis if available
                            if st.session_state.get(f"analysis_{idx}"):
                                with st.expander("Pulse Analysis", expanded=True):
                                    peek = st.session_state[f"analysis_{idx}"]["peek"]
                                    rc = st.session_state[f"analysis_{idx}"]["risk"]
                                    if isinstance(peek, dict):
                                        st.write(f"Confluence Score: {peek.get('score','—')}/100  •  Grade: {peek.get('grade','—')}")
                                        reasons = peek.get("reasons", [])
                                        if reasons:
                                            st.write("**Reasons:**")
                                            for r in reasons:
                                                st.write(f"• {r}")
                                    if isinstance(rc, dict):
                                        st.write(f"**Decision:** {rc.get('decision','—')}")
                                        flags = rc.get("behavioral_flags", [])
                                        if flags:
                                            st.write("**Behavioral Flags:** " + ", ".join(flags))
                    st.divider()
            else:
                st.info("No recent trades returned by the bridge.")

    with col2:
        # Behavioral insights
        if show_behavioral:
            render_behavioral_insights(pulse_manager)

    # Risk warnings
    st.markdown("---")
    st.subheader("⚠️ Risk Warnings")

    warnings = risk_data.get('warnings', [])
    
    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")
    else:
        st.success("✅ All risk parameters within limits")

    # Footer with last update time
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

# Helper: compute today's loss as % of SOD equity
def compute_daily_loss_pct(pulse_manager, account_info: Dict) -> float:
    """Return today's loss as % of SOD equity (positive means loss)."""
    try:
        sod = get_sod_equity(pulse_manager, account_info) or 0.0
        eq = float(account_info.get("equity", 0.0) or 0.0)
        if sod > 0:
            return max(0.0, (sod - eq) / sod * 100.0)
    except Exception:
        pass
    return 0.0
# === Injected: top Account Statistics + Recent Trades (runs once) ===
try:
    if not st.session_state.get("_patched_stats_rendered", False):
        rm = st.session_state.get("risk_manager")
        if rm is None:
            rm = PulseRiskManager()
            st.session_state["risk_manager"] = rm
        render_top_account_statistics(rm)
        render_recent_trades_section(rm, limit=10)
        st.session_state["_patched_stats_rendered"] = True
except Exception as _e:
    # Keep page resilient
    pass
def fetch_recent_trades_fallback(pulse_manager=None, limit: int = 10, days: int = 7) -> pd.DataFrame:
    """Fetch recent trades via MT5 HTTP bridge directly if manager method is unavailable."""
    mt5_url = None
    try:
        if pulse_manager is not None and hasattr(pulse_manager, 'mt5_url') and pulse_manager.mt5_url:
            mt5_url = pulse_manager.mt5_url
    except Exception:
        mt5_url = None
    if not mt5_url:
        mt5_url = os.getenv("MT5_URL", "http://mt5:5001")

    candidates = [
        f"history_deals_get?days={days}&limit={limit}",
        f"history_orders_get?days={days}&limit={limit}",
        f"history_deals_get?from={(datetime.now()-timedelta(days=days)).isoformat()}&to={datetime.now().isoformat()}&limit={limit}",
    ]
    for ep in candidates:
        try:
            r = requests.get(f"{mt5_url}/{ep}", timeout=2.0)
            if not r.ok:
                continue
            data = r.json() or []
            if not isinstance(data, list) or not data:
                continue
            df = pd.DataFrame(data)
            # normalize time column
            time_cols = [c for c in ["time", "time_msc", "time_done", "time_close"] if c in df.columns]
            if time_cols:
                col = time_cols[0]
                try:
                    df["time"] = pd.to_datetime(df[col], unit="s", errors="coerce")
                except Exception:
                    df["time"] = pd.to_datetime(df[col], errors="coerce")
            elif "timestamp" in df.columns:
                df["time"] = pd.to_datetime(df["timestamp"], errors="coerce")
            if "type" in df.columns:
                df["type"] = df["type"].replace({0: "BUY", 1: "SELL", 2: "BUY", 3: "SELL"})
            cols = [c for c in ["time","ticket","symbol","type","volume","price","price_open","price_current","profit","commission","swap","comment"] if c in df.columns]
            if "time" in cols:
                df = df.sort_values("time", ascending=False)
            return df[cols].head(limit) if cols else df.head(limit)
        except Exception:
            continue
    return pd.DataFrame()
