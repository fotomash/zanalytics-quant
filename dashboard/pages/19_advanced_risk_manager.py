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
        # Optional HTTP MT5 bridge (align with page 16)
        self.mt5_url = os.getenv("MT5_URL", "http://mt5:5001")
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

    def get_account_info(self) -> Dict:
        """Get account information via MT5 bridge first, then native. No mocks."""
        # HTTP bridge first
        if self.mt5_url:
            try:
                r = requests.get(f"{self.mt5_url}/account_info", timeout=2.0)
                if r.ok:
                    data = r.json() or {}
                    if isinstance(data, dict) and data:
                        self.bridge_available = True
                        self._last_account_info = data
                        return data
                else:
                    self.status_messages.append(f"HTTP bridge /account_info returned {r.status_code}")
            except Exception as e:
                self.status_messages.append(f"HTTP bridge error: {e}")
        # If we were previously connected and have a last good snapshot, reuse it on transient failures
        try:
            if self.connected and self._last_account_info:
                return self._last_account_info
        except Exception:
            pass

        # Try to (re)connect to MT5
        if not self.connected:
            self.connect()

        # If connected, pull live account info
        if self.connected:
            try:
                account_info = mt5.account_info()
                if account_info is not None:
                    info = {
                        'login': account_info.login,
                        'server': account_info.server,
                        'balance': account_info.balance,
                        'equity': account_info.equity,
                        'margin': account_info.margin,
                        'free_margin': account_info.margin_free,
                        'margin_level': account_info.margin_level,
                        'profit': account_info.profit,
                        'leverage': account_info.leverage,
                        'currency': account_info.currency,
                        'name': account_info.name,
                        'company': account_info.company,
                    }
                    self._last_account_info = info
                    return info
            except Exception as e:
                st.error(f"Error getting account info: {e}")

        # No live data — return last known good real snapshot if available
        if self._last_account_info:
            return self._last_account_info
        return {}

    def get_positions(self) -> pd.DataFrame:
        """Get all open positions with error handling (HTTP bridge first)."""
        # HTTP bridge first
        if self.mt5_url:
            try:
                r = requests.get(f"{self.mt5_url}/positions_get", timeout=2.0)
                if r.ok:
                    self.bridge_available = True
                    data = r.json() or []
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                        for col in ("time", "time_update"):
                            if col in df.columns:
                                try:
                                    df[col] = pd.to_datetime(df[col])
                                except Exception:
                                    pass
                        return df
            except Exception:
                pass
        # Native MT5
        try:
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

def create_risk_allocation_visualization(account_equity: float, 
                                       daily_risk_pct: float, 
                                       anticipated_trades: int,
                                       confluence_score: float = 75) -> go.Figure:
    """Create a cleaner, more attractive risk allocation chart"""

    # Calculate risk amounts
    daily_risk_amount = account_equity * (daily_risk_pct / 100)
    per_trade_risk = daily_risk_amount / max(anticipated_trades, 1)

    # Confidence-based adjustment
    confidence_multiplier = min(1.0, max(confluence_score, 0) / 100)
    adjusted_per_trade = per_trade_risk * confidence_multiplier

    categories = ['Daily Risk Budget', 'Per-Trade Risk', 'Adjusted Risk']
    values = [daily_risk_amount, per_trade_risk, adjusted_per_trade]
    colors = ['#2DD4BF', '#60A5FA', '#A78BFA']  # teal, blue, violet

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.25)', width=1)
        ),
        text=[f"${v:,.2f}" for v in values],
        textposition='outside',
        hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f"Risk Allocation",
            x=0.01, xanchor='left', y=0.95
        ),
        xaxis_title=None,
        yaxis_title="Risk Amount ($)",
        showlegend=False,
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='rgba(255,255,255,0.92)')
    )
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.08)', zerolinecolor='rgba(255,255,255,0.12)')

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
    """Render risk control panel"""
    
    st.subheader("🎛️ Risk Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Risk Parameters")
        
        # Daily risk slider with psychological guidance
        daily_risk_pct = st.slider(
            "Daily Risk Budget (%)", 
            0.5, 5.0, 2.0, 0.1,
            help="Maximum percentage of equity to risk today"
        )
        
        # Anticipated trades slider
        anticipated_trades = st.slider(
            "Anticipated Trades Today", 
            1, 10, 3,
            help="Number of trades you plan to take today"
        )
        
        # Calculate per-trade risk
        per_trade_risk = daily_risk_pct / anticipated_trades
        st.metric("Suggested Per-Trade Risk", f"{per_trade_risk:.2f}%", 
                 f"{anticipated_trades} trades planned")
    
    with col2:
        st.markdown("#### Risk Allocation")
        
        # Create risk allocation chart (do not guess equity)
        equity = account_info.get('equity')
        if equity is None:
            st.warning("No equity available from MT5 (not connected).")
        else:
            fig = create_risk_allocation_visualization(
                float(equity or 0), daily_risk_pct, anticipated_trades
            )
            st.plotly_chart(fig, use_container_width=True)

def render_psychology_insights_panel(confluence_data: Dict, risk_summary: Dict):
    """Render behavioral psychology insights panel"""
    
    st.subheader("🧠 Behavioral Psychology Insights")
    
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
    with st.expander("📚 Trading in the Zone Principles", expanded=False):
        for p in principles:
            st.write(f"✅ {p}")

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

def get_last_trade_snapshot() -> Dict:
    """Return last trade from API, falling back to Kafka if configured."""
    snap = _read_last_trade_via_api() or _read_last_trade_from_kafka()
    return snap or {}

def main():
    """Main dashboard function with comprehensive error handling"""
    
    st.title("🎯 Zanalytics Pulse — Advanced Risk Manager")
    st.markdown("### Live risk, behavior, and recent trades")

    # Initialize Advanced manager under a distinct key to avoid clashes with page 16
    if 'adv_pulse_manager' not in st.session_state or not isinstance(st.session_state.adv_pulse_manager, AdvancedPulseRiskManager):
        st.session_state.adv_pulse_manager = AdvancedPulseRiskManager()

    pulse_manager = st.session_state.adv_pulse_manager

    # System health status
    health_data = safe_api_call("GET", "pulse/health")
    if "error" not in health_data:
        status = health_data.get("status", "unknown")
        lag = health_data.get("lag_ms", "—")
        st.caption(f"System Status: {status} | Lag: {lag}ms | Last Update: {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.caption(f"System Status: offline | Last Update: {datetime.now().strftime('%H:%M:%S')}")

    # Get account information and risk status
    try:
        account_info = pulse_manager.get_account_info()
        positions_df = pulse_manager.get_positions()
        risk_data = pulse_manager.get_risk_summary()
        confluence_data = pulse_manager.get_confluence_score()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        account_info = {}
        positions_df = pd.DataFrame()
        risk_data = {}
        confluence_data = {}

    # Account banner
    login_banner = account_info.get("login")
    broker_banner = account_info.get("server") or account_info.get("company")
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

    # Advanced Risk Control Panel
    render_risk_control_panel(account_info, risk_data)
    
    # Behavioral Psychology Insights
    render_psychology_insights_panel(confluence_data, risk_data)
    
    # Divider
    st.divider()

    # Pulse Decision Surface
    render_pulse_tiles(pulse_manager)
    st.divider()

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

    # Top metrics row
    balance_val = float(account_info.get('balance', 0) or 0)
    equity_val = float(account_info.get('equity', 0) or 0)
    profit_val = float(account_info.get('profit', 0) or 0)
    margin_level_val = float(account_info.get('margin_level', 0) or 0)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("💰 Balance", f"${balance_val:,.2f}", f"${profit_val:,.2f}")

    with col2:
        equity = equity_val
        balance = balance_val if balance_val > 0 else 1.0
        equity_change = ((equity / balance - 1) * 100) if balance > 0 else 0
        
        st.metric(
            "📊 Equity",
            f"${equity:,.2f}",
            f"{equity_change:.2f}%"
        )

    with col3:
        st.metric("🎯 Margin Level", f"{margin_level_val:,.2f}%", "Safe" if margin_level_val > 200 else "Warning")

    with col4:
        # Temporarily mark as unavailable per feedback
        st.metric(
            "📈 Risk Used",
            "NA",
            "NA"
        )

    with col5:
        st.metric(
            "🔢 Open Positions",
            len(positions_df),
            f"Max: {risk_data.get('max_trades', 5)}"
        )

    # Risk metrics (temporarily not available)
    st.markdown("---")
    st.subheader("🎯 Risk Metrics")

    def _na_tile(title: str) -> None:
        st.markdown(
            f"""
            <div class=\"pulse-tile tile-plain\">
                <h4>{title}</h4>
                <h2>NA</h2>
                <p>Not available</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    gauge_col1, gauge_col2, gauge_col3, gauge_col4 = st.columns(4)
    with gauge_col1:
        _na_tile("Daily Risk Used (%)")
    with gauge_col2:
        _na_tile("Current Drawdown (%)")
    with gauge_col3:
        _na_tile("Trade Limit Usage (%)")
    with gauge_col4:
        _na_tile("Overall Risk Score")

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        # Trading opportunities
        render_opportunities(pulse_manager)

        # Open positions table
        if not positions_df.empty:
            st.subheader("📋 Open Positions")

            # Format positions dataframe
            display_cols = ['ticket', 'symbol', 'type', 'volume', 'price_open', 
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

    with col2:
        # Behavioral insights
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
