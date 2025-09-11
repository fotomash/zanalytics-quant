"""Pulse dashboard Streamlit page v2."""

import streamlit as st


def render_pnl_metric(live_data: dict) -> None:
    """Render today's P&L metric using Streamlit.

    Parameters
    ----------
    live_data: dict
        Dictionary containing ``pnl_today`` and ``pnl_change`` keys.
    """
    st.metric(
        label="Today's P&L",
        value=f"${live_data['pnl_today']:,.2f}",
        delta=live_data['pnl_change'],
        delta_color="normal",
    )


if __name__ == "__main__":
    sample = {"pnl_today": 1250.75, "pnl_change": -50.25}
    render_pnl_metric(sample)
"""Streamlit page for the intraday Pulse dashboard.

Configuration and prompt text are loaded from YAML and flat files. The page
then queries MT5 and Django REST services for account and position data and,
when enabled, posts trade actions back to the Django gateway. Retrieved data
drives the Streamlit UI to render real‑time trading metrics and controls.
"""

import os, json, time, uuid, datetime as dt
from typing import Any, Dict, List
import base64
import requests
import yaml
import streamlit as st
from dashboard.utils.plotly_donuts import oneway_donut
from dashboard.components import chip


# ---------------- Config ----------------
# Resolve paths relative to this file so the dashboard can be launched from any
# working directory. Environment variables still take precedence.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_METRICS_PATH = os.path.join(_SCRIPT_DIR, "..", "config", "dashboard_metrics_summary.yaml")
_DEFAULT_PROMPT_PATH = os.path.join(_SCRIPT_DIR, "..", "config", "dashboard_prompt.txt")

METRICS_PATH = os.getenv('DASH_METRICS_PATH', _DEFAULT_METRICS_PATH)
PROMPT_PATH  = os.getenv('DASH_PROMPT_PATH',  _DEFAULT_PROMPT_PATH)

MT5_URL     = os.getenv('MT5_URL', 'http://mt5:5001')
DJANGO_URL  = os.getenv('DJANGO_API_URL', 'http://django:8000')
DJANGO_PREF = os.getenv('DJANGO_API_PREFIX', '/api/v1')

BRIDGE_TOKEN = os.getenv('BRIDGE_TOKEN')
GATEWAY_HEADERS = {'X-Bridge-Token': BRIDGE_TOKEN} if BRIDGE_TOKEN else {}
ACTIONS_URL = f"{DJANGO_URL}{DJANGO_PREF}/actions/query"

# ---------------- Utils ----------------
@st.cache_data(ttl=5.0)
def load_yaml(path: str) -> Dict[str, Any]:
    """Return the contents of a YAML file.

    Parameters
    ----------
    path: str
        File system path to the YAML document.

    Returns
    -------
    dict
        Parsed YAML data or an empty dictionary if the file is empty.

    Raises
    ------
    OSError
        If the file cannot be opened.
    yaml.YAMLError
        On malformed YAML content.
    """

    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

@st.cache_data(ttl=5.0)
def load_prompt(path: str) -> str:
    """Load a text prompt from ``path``.

    Parameters
    ----------
    path: str
        Location of the plain-text prompt file.

    Returns
    -------
    str
        Stripped file contents, or ``""`` if the file is missing.

    Raises
    ------
    OSError
        If the file exists but cannot be read.
    """

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ''

def get_json(url: str, headers=None, timeout=3):
    """HTTP GET ``url`` and parse a JSON response.

    Parameters
    ----------
    url: str
        Endpoint to query.
    headers: dict | None
        Optional request headers.
    timeout: int
        Seconds before the request times out.

    Returns
    -------
    Any | None
        Decoded JSON content, or ``None`` if the request fails or the response
        is not valid JSON.

    Error Handling
    --------------
    Network or JSON parsing exceptions are suppressed and result in ``None``.
    """

    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def post_actions(body: Dict[str, Any], idempotency_key: str | None = None, timeout=5):
    """Send an action request to the Django gateway.

    Parameters
    ----------
    body: dict
        JSON-serialisable payload describing the action.
    idempotency_key: str | None
        Optional key to guard against duplicate submissions.
    timeout: int
        Request timeout in seconds.

    Returns
    -------
    tuple[bool, dict]
        ``(ok, data)`` where ``ok`` indicates HTTP success and ``data`` is the
        parsed JSON response or an error description.

    Error Handling
    --------------
    Network failures or invalid JSON responses return ``(False, {'error':
    message})``.
    """

    headers = {'Content-Type': 'application/json'}
    if idempotency_key:
        headers['X-Idempotency-Key'] = idempotency_key
    try:
        r = requests.post(ACTIONS_URL, json=body, headers=headers, timeout=timeout)
        ok = r.ok
        data = None
        try:
            data = r.json()
        except Exception:
            data = {'text': r.text}
        return ok, data
    except Exception as e:
        return False, {'error': str(e)}


def close_position(ticket: int):
    """Request a full close for ``ticket`` via the Django gateway."""
    if not st.session_state.get('enable_actions'):
        return
    with st.spinner('Closing...'):
        ok, data = post_actions(
            {'type': 'position_close', 'payload': {'ticket': ticket}},
            idempotency_key=f"close-{ticket}-{uuid.uuid4().hex[:8]}",
        )
    st.session_state['last_action'] = (
        ('success', 'Close requested')
        if ok
        else ('error', f"Close failed: {data}")
    )


def partial_close(ticket: int, fraction: float):
    """Request a partial close of ``fraction`` for ``ticket``."""
    if not st.session_state.get('enable_actions'):
        return
    with st.spinner(f"Partial closing {fraction * 100:.0f}%..."):
        ok, data = post_actions(
            {
                'type': 'position_close',
                'payload': {'ticket': ticket, 'fraction': fraction},
            },
            idempotency_key=f"p{int(fraction * 100)}-{ticket}-{uuid.uuid4().hex[:8]}",
        )
    st.session_state['last_action'] = (
        ('success', 'Partial requested')
        if ok
        else ('error', f"Partial failed: {data}")
    )



@st.cache_data(ttl=3600)
def get_image_as_base64(path: str) -> str | None:
    """Return a base64 encoded string for the image at ``path``."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None


def apply_advanced_styling() -> str:
    """CSS for metrics, buttons, tabs, and tiles."""
    return """
    <style>
    /* Enhanced metrics */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
        border-color: rgba(59, 130, 246, 0.5);
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(26, 29, 58, 0.5);
        border-radius: 10px;
        padding: 0.5rem;
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #94a3b8;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
    }
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(59, 130, 246, 0.4);
    }
    /* Cards */
    .dashboard-card {
        background: rgba(26, 29, 58, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    </style>
    """




def dim_block(start: bool = True):
    """Context manager helper to dim or restore a UI block.

    Parameters
    ----------
    start: bool
        When ``True`` begin a dimmed block; otherwise close the block.

    Returns
    -------
    None
        Emits opening or closing markup to the page.
    """

    if start:
        st.markdown("<div style='opacity:0.5; pointer-events:none;'>", unsafe_allow_html=True)
    else:
        st.markdown("</div>", unsafe_allow_html=True)

def get_account_info():
    """Fetch MT5 account information.

    Returns
    -------
    dict | None
        Parsed JSON payload or ``None`` on error.
    """

    return get_json(f"{MT5_URL}/account_info", headers=GATEWAY_HEADERS, timeout=3)

def get_positions() -> List[Dict[str, Any]]:
    """Return the list of open MT5 positions.

    Returns
    -------
    list[dict]
        A list of position dictionaries; empty on error.
    """

    return get_json(f"{MT5_URL}/positions_get", headers=GATEWAY_HEADERS, timeout=3) or []

def get_session_time_remaining():
    """Compute time remaining until the end of the trading session (21:00 UTC).

    Returns
    -------
    datetime.timedelta
        Time remaining until session close.
    """

    now = dt.datetime.utcnow()
    end = now.replace(hour=21, minute=0, second=0, microsecond=0)
    if now > end:
        end = end + dt.timedelta(days=1)
    return (end - now)

def pnl_unrealized(positions: list) -> float:
    """Aggregate unrealised profit across ``positions``.

    Parameters
    ----------
    positions: list
        Sequence of MT5 position dictionaries.

    Returns
    -------
    float
        Sum of the ``profit`` field for each position; missing values count as
        ``0``.
    """

    return float(sum(float(p.get('profit', 0.0)) for p in positions))

def exposure_percent_stub(positions: list, account: dict) -> float:
    """Placeholder exposure metric until risk engine integration.

    Parameters
    ----------
    positions: list
        Current open positions.
    account: dict
        MT5 account info (currently unused).

    Returns
    -------
    float
        Simple percentage based on the number of positions.
    """

    # ↪ Replace with live risk_enforcer metric when available
    return min(100.0, max(0.0, 10.0 * len(positions)))

def type_to_text(t: int) -> str:
    """Convert MT5 position type ``t`` to a human readable string.

    Parameters
    ----------
    t: int
        ``0`` for buy, ``1`` for sell; other values are returned as-is.

    Returns
    -------
    str
        Human readable text representing the position type.
    """

    return 'BUY' if int(t) == 0 else 'SELL' if int(t) == 1 else str(t)

def secs_to_hms(seconds: int) -> str:
    """Convert seconds to ``H:MM:SS``; ``'—'`` if ``seconds`` <= 0.

    Parameters
    ----------
    seconds: int
        Number of seconds to convert.

    Returns
    -------
    str
        ``H:MM:SS`` formatted string or ``'—'`` if ``seconds`` <= 0.
    """

    if seconds <= 0:
        return '—'
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}"

# ---------------- UI ----------------
st.set_page_config(
    page_title='Pulse – Intraday',
    page_icon='🫀',
    layout='wide',
    initial_sidebar_state='expanded'
)

_img_base64 = get_image_as_base64("image_af247b.jpg")
if _img_base64:
    _background_style = f"""
    <style>
    [data-testid=\"stAppViewContainer\"] > .main {{
        background-image: linear-gradient(rgba(0,0,0,0.80), rgba(0,0,0,0.80)), url(data:image/jpeg;base64,{_img_base64});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    .main .block-container {{
        background-color: rgba(0,0,0,0.025) !important;
    }}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.markdown(_background_style, unsafe_allow_html=True)

st.markdown(apply_advanced_styling(), unsafe_allow_html=True)
st.title('Pulse – Intraday Trader View')

metrics_cfg = load_yaml(METRICS_PATH)
soft_prompt = load_prompt(PROMPT_PATH)

colA, colB = st.columns([2, 1])
with colA:
    st.caption('Real-time, high-signal metrics with behavioral overlays.')
with colB:
    if soft_prompt:
        with st.expander('Soft Prompt (session guidance)'):
            st.write(soft_prompt)

# Data fetch
account = get_account_info()
positions = get_positions()

# ---------------- Session Metrics ----------------
st.subheader('Session')
sm = metrics_cfg.get('session_metrics', {})
sess_cols = st.columns(4)

if sm.get('start_of_day_balance', False):
    with sess_cols[0]:
        bal = account.get('balance') if account else None
        if bal is None:
            dim_block(True); st.metric('Start of Day Balance', '—'); dim_block(False)
        else:
            st.metric('Start of Day Balance', f"{bal:,.2f}")

if sm.get('current_equity', False):
    with sess_cols[1]:
        eq = account.get('equity') if account else None
        if eq is None:
            dim_block(True); st.metric('Current Equity', '—'); dim_block(False)
        else:
            st.metric('Current Equity', f"{eq:,.2f}")

if sm.get('daily_risk_allowance_percent', False) or sm.get('current_risk_used_percent', False):
    with sess_cols[2]:
        # ↪ Replace with live risk_enforcer metrics
        risk_allow = 2.0  # %
        risk_used = 0.8  # %
        st.plotly_chart(
            oneway_donut(
                title="Risk Used",
                frac=risk_used / risk_allow if risk_allow else 0.0,
                start_anchor="bottom",
                center_title=f"{risk_used:.1f}%",
                center_sub=f"of {risk_allow:.1f}%",
            ),
            use_container_width=True,
        )


if sm.get('session_time_remaining', False):
    with sess_cols[3]:
        rem = get_session_time_remaining()
        st.metric('Session Time Remaining', str(rem).split('.')[0] if rem else '—')

# ---------------- Trade Metrics ----------------
st.subheader('Trades')
tm = metrics_cfg.get('trade_metrics', {})
tcols = st.columns(4)

if tm.get('unrealized_pnl', False):
    with tcols[0]:
        upnl = pnl_unrealized(positions)
        st.metric('Unrealized PnL', f"{upnl:,.2f}")
        chip('Live', 'good' if positions else 'neutral')

if tm.get('time_in_trade', False):
    with tcols[1]:
        # Show max time-in-trade across open positions (placeholder if times absent)
        now = int(time.time())
        durations = []
        for p in positions:
            t_open = int(p.get('time', 0))  # MT5 positions usually include 'time'
            if t_open > 0:
                durations.append(now - t_open)
        if durations:
            st.metric('Time in Trade (max)', secs_to_hms(max(durations)))
        else:
            dim_block(True); st.metric('Time in Trade', '—'); dim_block(False)

if tm.get('exposure_percent', False):
    with tcols[2]:
        exp = exposure_percent_stub(positions, account)
        st.plotly_chart(
            oneway_donut(
                title="Exposure",
                frac=exp / 100 if exp is not None else 0.0,
                start_anchor="bottom",
                center_title=f"{exp:.0f}%",
            ),
            use_container_width=True,
        )


if tm.get('max_adverse_excursion', False):
    with tcols[3]:
        dim_block(True); st.metric('Max Adverse Excursion', '—'); dim_block(False)
# ---------------- Behavioral Metrics ----------------
st.subheader('Behavior')
bm = metrics_cfg.get('behavioral_metrics', {})
bcols = st.columns(5)

def placeholder_chip(name: str):
    """Render a placeholder chip noting that ``name`` is pending.

    Parameters
    ----------
    name: str
        Name of the metric being represented.

    Returns
    -------
    None
        The placeholder pill is added to the page.
    """

    with st.container():
        dim_block(True); chip(f"{name}: pending", 'neutral'); dim_block(False)

if bm.get('composite_posture_score', False):
    with bcols[0]: placeholder_chip('Posture')
if bm.get('patience_index', False):
    with bcols[1]: placeholder_chip('Patience')
if bm.get('conviction_accuracy', False):
    with bcols[2]: placeholder_chip('Conviction')
if bm.get('profit_efficiency', False):
    with bcols[3]: placeholder_chip('Profit Eff.')
if bm.get('overtrading_alert', False):
    with bcols[4]: chip('Overtrading: OK', 'good')  # ↪ Replace with live journal count vs. limits

# ---------------- Future Signals ----------------
st.subheader('Future Signals')
fs = metrics_cfg.get('future_signals', {})
fcols = st.columns(3)
with fcols[0]:
    # ↪ Wire to news/calendar microservice; placeholder until live
    dim_block(True); st.metric('Next News Release', '—'); dim_block(False)
with fcols[1]:
    dim_block(True); chip('Context Alerts: —', 'neutral'); dim_block(False)
with fcols[2]:
    dim_block(True); chip('Whisperer Rating: —', 'neutral'); dim_block(False)

st.caption('Gray elements indicate metrics not yet live or awaiting data.')

# ---------------- Position Manager ----------------
st.subheader('Open Positions')
if not positions:
    st.info('No open positions.')
else:
    st.checkbox('Enable trade actions', key='enable_actions', value=False, help='Guardrail to prevent accidental clicks')
    if 'last_action' in st.session_state:
        status, msg = st.session_state.pop('last_action')
        getattr(st, status)(msg)
    for i, p in enumerate(positions):
        with st.container():
            cols = st.columns([2, 1, 1, 1, 1, 2])
            cols[0].markdown(f"**{p.get('symbol','')}**")
            type_text = p.get('type', 'BUY').upper()
            type_color = 'green' if type_text == 'BUY' else 'red'
            cols[1].markdown(
                f"<span style='color:{type_color}'>{type_text}</span>",
                unsafe_allow_html=True,
            )
            cols[2].markdown(f"Vol: {float(p.get('volume',0.0)):.2f}")
            cols[3].markdown(f"Open: {float(p.get('price_open',0.0)):.5f}")
            cols[4].markdown(f"P/L: {float(p.get('profit',0.0)):.2f}")
            with cols[5]:
                ticket = int(p.get('ticket'))
                btn_c1, btn_c2 = st.columns(2)
                btn_c1.button(
                    'Partial 50%',
                    key=f"p50_{ticket}",
                    use_container_width=True,
                    disabled=not st.session_state.enable_actions,
                    on_click=partial_close,
                    args=(ticket, 0.5),
                )
                btn_c2.button(
                    'Close',
                    key=f"close_{ticket}",
                    use_container_width=True,
                    disabled=not st.session_state.enable_actions,
                    on_click=close_position,
                    args=(ticket,),
                )

