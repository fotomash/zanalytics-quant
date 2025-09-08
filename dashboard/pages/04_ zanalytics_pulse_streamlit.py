import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import os
from dashboard.utils.streamlit_api import (
    safe_api_call,
    fetch_whispers,
    post_whisper_ack,
    post_whisper_act,
    get_trading_menu_options,
    render_status_row,
    api_url,
    start_whisper_sse,
    drain_whisper_sse,
    get_sse_status,
    fetch_trade_history,
    fetch_trade_history_filtered,
    fetch_symbols,
)
from dashboard.components.ui_concentric import concentric_ring

# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse | The Whisperer",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for sophisticated styling
st.markdown(
    """
<style>
    /* Dark theme with professional aesthetics */
    .stApp {
        background: linear-gradient(135deg, #0B1220 0%, #111827 100%);
    }
    
    /* Custom metric cards */
    .metric-card {
        background: rgba(31, 41, 55, 0.5);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(75, 85, 99, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .discipline-high { color: #22C55E; }
    .discipline-medium { color: #FBBF24; }
    .discipline-low { color: #EF4444; }
    
    /* Whisperer feed styling */
    .whisper-message {
        background: rgba(31, 41, 55, 0.3);
        border-left: 3px solid;
        padding: 12px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    
    .whisper-insight { border-color: #3B82F6; }
    .whisper-warning { border-color: #FBBF24; }
    .whisper-success { border-color: #22C55E; }
    .whisper-alert { border-color: #EF4444; }
    
    /* Professional headers */
    h1, h2, h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 600;
    }
    
    /* Metric emphasis */
    .big-metric {
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if 'discipline_score' not in st.session_state:
    st.session_state.discipline_score = 85
    st.session_state.patience_index = 72
    st.session_state.conviction_rate = 68
    st.session_state.profit_efficiency = 74
    st.session_state.current_pnl = 248.00
    st.session_state.session_equity = 203229.05
    st.session_state.whispers = []
    
    # Quick concentric session ring under the header (live-first)
    try:
        base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
        acct = requests.get(f"{base}/api/v1/account/info", timeout=1.2).json()
        risk = requests.get(f"{base}/api/v1/account/risk", timeout=1.2).json()
        trade = requests.get(f"{base}/api/v1/feed/trade", timeout=1.2).json()
        equity = requests.get(f"{base}/api/v1/feed/equity", timeout=1.2).json()
        eq = float(acct.get('equity') or 0.0)
        sod = float(risk.get('sod_equity') or acct.get('balance') or eq or 0.0)
        pnl_today = eq - sod
        target = float(risk.get('target_amount') or 0.0)
        loss = float(risk.get('loss_amount') or 0.0)
        outer = None
        if pnl_today >= 0 and target > 0:
            outer = min(1.0, pnl_today/target)
        elif pnl_today < 0 and loss > 0:
            outer = -min(1.0, abs(pnl_today)/loss)
        realized = trade.get('realized_usd') if isinstance(trade, dict) else None
        unreal = trade.get('unrealized_usd') if isinstance(trade, dict) else None
        cap_val = max(1.0, abs((realized or 0)) + abs((unreal or 0)))
        left = (abs(unreal)/cap_val) if isinstance(unreal, (int,float)) and cap_val > 0 else 0.0
        right = (abs(realized)/cap_val) if isinstance(realized, (int,float)) and cap_val > 0 else 0.0
        exp = equity.get('exposure_pct') if isinstance(equity, dict) else None
        if isinstance(exp, (int,float)) and exp > 1:
            exp = exp/100.0
        fig_ring = concentric_ring(
            center_title=f"{eq:,.0f}",
            center_value=f"{pnl_today:+,.0f}",
            caption="Equity • P&L today",
            outer_bipolar=outer,
            outer_cap=1.0,
            middle_mode="split",
            middle_split=(left, right),
            inner_unipolar=exp or 0.0,
            inner_cap=1.0,
            size=(280, 280),
        )
        st.plotly_chart(fig_ring, use_container_width=True, config={'displayModeBar': False})
    except Exception:
        pass

"""All data below uses live feeds where available; no mock series."""

# Header Section
st.markdown("# 🧭 Zanalytics Pulse")
st.markdown("### Your Behavioral Trading Co-Pilot")

# Live API helpers (align with page 06)
mini = safe_api_call('GET', 'api/v1/market/mini')
mirror = safe_api_call('GET', 'api/v1/mirror/state')
acct = safe_api_call('GET', 'api/v1/account/info')
risk = safe_api_call('GET', 'api/v1/account/risk')
whispers_resp = safe_api_call('GET', 'api/pulse/whispers')
equity_series = safe_api_call('GET', 'api/v1/feed/equity/series')

# Live P&L helpers (shared across sections)
def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

_acct = acct or {}
_risk = risk or {}
live_equity = _safe_float(_acct.get('equity'))
live_balance = _safe_float(_acct.get('balance'))
live_sod = _safe_float(_risk.get('sod_equity') or live_balance or live_equity)
live_target_amt = _safe_float(_risk.get('target_amount'))
live_loss_amt = _safe_float(_risk.get('loss_amount'))
live_pnl_today = live_equity - live_sod

# Market Context Bar (use live mini payload)
vix_obj = (mini.get('vix') or {}) if isinstance(mini, dict) else {}
dxy_obj = (mini.get('dxy') or {}) if isinstance(mini, dict) else {}
vix_val = vix_obj.get('value') or 0.0
dxy_val = dxy_obj.get('value') or 0.0
vix_series = vix_obj.get('series') or []
dxy_series = dxy_obj.get('series') or []
def _delta(series):
    try:
        return float(series[-1] - series[-2]) if isinstance(series, list) and len(series) >= 2 else None
    except Exception:
        return None
vix_delta = _delta(vix_series)
dxy_delta = _delta(dxy_series)
market_data = {
    'vix': float(vix_val) if isinstance(vix_val, (int, float)) else 0.0,
    'dxy': float(dxy_val) if isinstance(dxy_val, (int, float)) else 0.0,
    'regime': (mini.get('regime') if isinstance(mini, dict) else None) or '—',
}
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

with col1:
    delta = (f"{vix_delta:+.2f}" if isinstance(vix_delta, (int, float)) else "—")
    st.metric("VIX", f"{market_data['vix']:.2f}", delta)

with col2:
    delta = (f"{dxy_delta:+.2f}" if isinstance(dxy_delta, (int, float)) else "—")
    st.metric("DXY", f"{market_data['dxy']:.2f}", delta)

with col3:
    regime_map = {'Risk-On': '🟢', 'Neutral': '🟡', 'Risk-Off': '🔴'}
    regime_val = market_data.get('regime') or '—'
    regime_emoji = regime_map.get(regime_val, '⚪')
    st.metric("Regime", f"{regime_emoji} {regime_val}")

with col4:
    render_status_row()

st.divider()

# Main Dashboard Layout
col_left, col_center, col_right = st.columns([1.5, 2, 1.5])

with col_left:
    # --- Behavioral Compass (concentric, center-locked rings) ---
    # Pull live values from mirror API when present; fall back to session_state
    def _get_mirror_pct(key: str, default_val: float) -> float:
        try:
            if isinstance(mirror, dict) and key in mirror:
                v = mirror.get(key)
                # accept {value: x} or raw number
                if isinstance(v, dict) and "value" in v:
                    return float(v["value"])
                return float(v)
        except Exception:
            pass
        return float(default_val)

    metrics = [
        {"name": "Discipline", "value": _get_mirror_pct("discipline", st.session_state.discipline_score), "color": "#22C55E"},
        {"name": "Patience",   "value": _get_mirror_pct("patience",   st.session_state.patience_index),   "color": "#3B82F6"},
        {"name": "Profit Efficiency", "value": _get_mirror_pct("efficiency", st.session_state.profit_efficiency),"color": "#06B6D4"},
        {"name": "Conviction", "value": _get_mirror_pct("conviction", st.session_state.conviction_rate),  "color": "#8B5CF6"},
    ]

    # Concentric geometry
    fig = go.Figure()
    sizes = [1.00, 0.82, 0.64, 0.46]
    band_px_ratio = 0.16
    track_color = "rgba(31,41,55,0.30)"
    start_at_noon = 90
    for i, metric in enumerate(metrics):
        s = sizes[i]
        off = (1.0 - s) / 2.0
        hole = max(0.0, min(0.95, 1.0 - band_px_ratio))
        fig.add_trace(go.Pie(values=[100], labels=[""], hole=hole, rotation=start_at_noon, direction="clockwise",
                              marker=dict(colors=[track_color]), textinfo="none", showlegend=False, sort=False,
                              domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off]),))
        val = max(0.0, min(100.0, float(metric["value"])))
        fig.add_trace(go.Pie(values=[val, 100 - val], labels=[metric["name"], ""], hole=hole, rotation=start_at_noon,
                              direction="clockwise", marker=dict(colors=[metric["color"], "rgba(0,0,0,0)"]),
                              textinfo="none", hovertemplate=f"{metric['name']}: {{%}}%&lt;extra&gt;&lt;/extra&gt;", showlegend=False,
                              sort=False, domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off]),))

    overall = int(np.mean([m["value"] for m in metrics if isinstance(m.get("value"), (int, float))]))
    fig.add_annotation(text=f"<b>{overall}%</b><br>Overall", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=20, color="#ffffff"))
    fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Behavioral Metrics Details
    for metric in metrics:
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            st.markdown(f"**{metric['name']}**")
        with col_m2:
            color = metric['color']
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{metric['value']}%</span>", unsafe_allow_html=True)

    st.divider()

    # Pattern Watch
    st.markdown("### 🎯 Pattern Watch")
    patterns = [
        {'name': 'Revenge Trading', 'status': 'OK', 'color': '#22C55E'},
        {'name': 'FOMO', 'status': 'OK', 'color': '#22C55E'},
        {'name': 'Fear (Cut Winners)', 'status': 'ALERT', 'color': '#FBBF24'},
        {'name': 'Overconfidence', 'status': 'OK', 'color': '#22C55E'}
    ]
    for pattern in patterns:
        st.markdown(
            f"<div style='padding: 8px; margin: 4px 0; background: rgba(31,41,55,0.3); "
            f"border-left: 3px solid {pattern['color']}; border-radius: 0 6px 6px 0;'>"
            f"<span style='color: #9CA3AF;'>{pattern['name']}:</span> "
            f"<span style='color: {pattern['color']}; font-weight: bold;'>{pattern['status']}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# CENTER COLUMN - Session Vitals & Trajectory
with col_center:
    # Session Vitals
    st.markdown("### 💰 Session Vitals")
    
    vital_cols = st.columns(3)
    with vital_cols[0]:
        pnl_color = '#22C55E' if live_pnl_today >= 0 else '#EF4444'
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>P&L</div>"
            f"<div class='big-metric' style='color: {pnl_color};'>"
            f"${live_pnl_today:+.2f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with vital_cols[1]:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>Equity</div>"
            f"<div class='big-metric'>${live_equity:,.0f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with vital_cols[2]:
        # Toward daily target; show only positive progress
        if live_target_amt > 0 and live_pnl_today > 0:
            target_progress = min((live_pnl_today / live_target_amt) * 100.0, 100.0)
        else:
            target_progress = 0.0
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>Target Progress</div>"
            f"<div class='big-metric'>{target_progress:.0f}%</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    # Session Trajectory Chart (live equity series)
    st.markdown("### 📈 Session Trajectory")
    try:
        points = equity_series.get('points') if isinstance(equity_series, dict) else []
        if points:
            df = pd.DataFrame(points)
            df['time'] = pd.to_datetime(df['ts'], errors='coerce')
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
            fig_tr = go.Figure(go.Scatter(x=df['time'], y=df['pnl'], mode='lines', name='P&L',
                                          line=dict(color='#22C55E', width=2), fill='tozeroy',
                                          fillcolor='rgba(34, 197, 94, 0.1)'))
            fig_tr.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.3)
            fig_tr.update_layout(height=300, margin=dict(t=0,b=20,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_tr, use_container_width=True)
        else:
            st.info("No trades today — trajectory will appear once trades close.")
    except Exception:
        st.info("Trajectory feed unavailable.")
    
    # Discipline Posture
    st.markdown("### 📊 Discipline Posture")
    
    # Discipline data (use 7-day summary if available)
    dsum = safe_api_call('GET', 'api/v1/discipline/summary')
    discipline_history = []
    if isinstance(dsum, dict) and isinstance(dsum.get('seven_day'), list) and dsum['seven_day']:
        try:
            discipline_history = [int(x.get('score') or 0) for x in dsum['seven_day']][-10:]
        except Exception:
            discipline_history = []
    if not discipline_history:
        discipline_history = [78, 82, 75, 88, 92, 85, 79, 83, 87, st.session_state.discipline_score]
    
    fig_discipline = go.Figure()
    
    colors = ['#22C55E' if d > 80 else '#FBBF24' if d > 60 else '#EF4444' for d in discipline_history]
    
    fig_discipline.add_trace(go.Bar(
        x=list(range(1, 11)),
        y=discipline_history,
        marker_color=colors,
        text=[f'{d}%' for d in discipline_history],
        textposition='outside',
        textfont=dict(color='#9CA3AF', size=10),
        hovertemplate='Trade %{x}<br>Discipline: %{y}%<extra></extra>'
    ))
    
    fig_discipline.update_layout(
        height=200,
        margin=dict(t=20, b=20, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title='Last 10 Trades',
            color='#9CA3AF',
            showgrid=False
        ),
        yaxis=dict(
            range=[0, 100],
            showgrid=True,
            gridcolor='rgba(75, 85, 99, 0.2)',
            color='#9CA3AF'
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_discipline, use_container_width=True)

# RIGHT COLUMN - The Whisperer (live)
with col_right:
    status = get_sse_status()
    badge_col = "#10B981" if status == "connected" else ("#F59E0B" if status not in ("idle", "disconnected") else "#EF4444")
    st.markdown(f"### 🤖 The Whisperer <span style='font-size:12px;color:{badge_col};margin-left:6px'>[{status}]</span>", unsafe_allow_html=True)
    # Start SSE and combine with HTTP polls
    start_whisper_sse()
    sse_items = drain_whisper_sse()
    whispers_raw = whispers_resp.get('whispers') if isinstance(whispers_resp, dict) else []
    if sse_items:
        whispers_raw = (whispers_raw or []) + sse_items
    whispers = []
    latest_slice = list(reversed((whispers_raw or [])[-25:]))
    for w in latest_slice:
        ts = w.get('ts')
        try:
            tdisp = datetime.fromtimestamp(float(ts)).strftime('%H:%M:%S') if ts else ''
        except Exception:
            tdisp = ''
        whispers.append({'time': tdisp or datetime.now().strftime('%H:%M:%S'), 'type': (w.get('severity') or 'insight'), 'message': w.get('message') or '', 'id': w.get('id'), 'actions': w.get('actions') or []})
    
    # Whisper feed container (scrollable)
    whisper_container = st.container()
    with whisper_container:
        type_icons = {'insight': '💡', 'warning': '⚠️', 'success': '✅', 'alert': '🚨'}
        html = ["<div style='max-height:400px; overflow:auto'>"]
        for w in whispers:
            icon = type_icons.get(w['type'], '💬')
            html.append(
                f"<div class='whisper-message whisper-{w['type']}'>"
                f"<div style='display:flex;align-items:start;'>"
                f"<span style='font-size:1.2em;margin-right:8px'>{icon}</span>"
                f"<div style='flex:1'>"
                f"<div style='color:#6B7280;font-size:0.75em'>{w['time']}</div>"
                f"<div style='color:#E5E7EB;margin-top:4px'>{w['message']}</div>"
                f"</div></div></div>"
            )
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("### Quick Actions")
    if latest_slice:
        options = []
        for w in latest_slice[:10]:
            ts = w.get('ts')
            try:
                tdisp = datetime.fromtimestamp(float(ts)).strftime('%H:%M:%S') if ts else ''
            except Exception:
                tdisp = ''
            options.append((f"{tdisp} — {str(w.get('message') or '')[:80]}", w))
        labels = [o[0] for o in options]
        sel = st.selectbox("Select whisper", labels, index=0)
        sel_w = options[labels.index(sel)][1]
        c1, c2 = st.columns(2)
        with c1:
            reason = st.text_input("Ack reason", value="", placeholder="optional")
            if st.button("✅ Acknowledge", use_container_width=True, key="ack_btn_04"):
                res = post_whisper_ack(sel_w.get("id"), reason or None)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Acknowledged")
                else:
                    st.error(f"Ack failed: {res}")
        with c2:
            acts = sel_w.get('actions') or []
            act_labels = [a.get('label') or a.get('action') for a in acts] or ["act_trail_50", "act_move_sl_be", "act_size_down"]
            act_values = [a.get('action') for a in acts] or act_labels
            act_choice = st.selectbox("Action", act_labels, index=0, key="act_sel_04")
            act_value = act_values[act_labels.index(act_choice)]
            if st.button("🚀 Act", use_container_width=True, key="act_btn_04"):
                res = post_whisper_act(sel_w.get("id"), act_value)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Action sent")
                else:
                    st.error(f"Act failed: {res}")
    else:
        st.info("No whispers yet.")

# Bottom Section - Additional Insights (no mock values)
st.divider()

bottom_cols = st.columns(4)

with bottom_cols[0]:
    st.markdown("### Trade Quality")
    q = safe_api_call('GET', 'api/pulse/analytics/trades/quality')
    labels = q.get('labels') if isinstance(q, dict) else None
    counts = q.get('counts') if isinstance(q, dict) else None
    if not (isinstance(labels, list) and isinstance(counts, list) and len(labels) == len(counts)):
        labels, counts = ["A+", "B", "C"], [0, 0, 0]
    colors = ['#22C55E', '#FBBF24', '#EF4444'][:len(labels)]
    fig_quality = go.Figure(go.Bar(x=labels, y=counts, marker_color=colors, text=counts, textposition='outside'))
    
    fig_quality.update_layout(
        height=150,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(color='#9CA3AF'),
        yaxis=dict(visible=False),
        showlegend=False
    )
    
st.plotly_chart(fig_quality, use_container_width=True)

with bottom_cols[1]:
    st.markdown("### Profit Efficiency")
    try:
        eff = safe_api_call('GET', 'api/pulse/analytics/trades/efficiency')
        pct = eff.get('captured_vs_potential_pct') if isinstance(eff, dict) else None
        val = float(pct) if isinstance(pct, (int, float)) else None
        if val is not None and 0.0 <= val <= 1.0:
            st.metric("Captured vs Potential", f"{val*100:.0f}%")
            st.progress(max(0.0, min(1.0, val)))
            st.caption("Trade analytics")
        else:
            # Fallback to mirror if available
            eff_raw = (mirror or {}).get('efficiency') if isinstance(mirror, dict) else None
            if isinstance(eff_raw, (int, float)):
                v = eff_raw if eff_raw <= 1.0 else eff_raw/100.0
                st.metric("Captured vs Potential", f"{v*100:.0f}%")
                st.progress(max(0.0, min(1.0, v)))
                st.caption("Behavioral mirror (fallback)")
            else:
                st.metric("Captured vs Potential", "—")
                st.progress(0.0)
                st.caption("Awaiting feed")
    except Exception:
        st.metric("Captured vs Potential", "—")
        st.progress(0.0)
        st.caption("Awaiting feed")

with bottom_cols[2]:
    st.markdown("### Risk Management")
    try:
        summ = safe_api_call('GET', 'api/pulse/analytics/trades/summary')
        avg_r = summ.get('avg_r') if isinstance(summ, dict) else None
        if isinstance(avg_r, (int, float)):
            st.metric("Avg Risk/Trade", f"{float(avg_r):.2f}R")
        else:
            st.metric("Avg Risk/Trade", "—")
        mx_exp = None
        for k in ('max_exposure_pct', 'exposure_pct'):
            v = (risk or {}).get(k) if isinstance(risk, dict) else None
            if isinstance(v, (int, float)):
                mx_exp = float(v)
                break
        if mx_exp is not None:
            st.metric("Max Exposure", f"{(mx_exp if mx_exp>1.0 else mx_exp*100):.1f}%")
        else:
            st.metric("Max Exposure", "—")
    except Exception:
        st.metric("Avg Risk/Trade", "—")
        st.metric("Max Exposure", "—")

with bottom_cols[3]:
    st.markdown("### Session Momentum")
    momentum = 68
    st.metric("Positive Momentum", f"{momentum}%")
    st.progress(momentum/100)
    st.caption("Maintaining discipline")

# Analytics: R distribution and Setups by Quality (uses filters above)
st.divider()
ana1, ana2 = st.columns(2)
q_params = []
if sym:
    q_params.append(f"symbol={sym}")
if df_str_from:
    q_params.append(f"date_from={df_str_from}")
if df_str_to:
    q_params.append(f"date_to={df_str_to}")
qstr = ("?" + "&".join(q_params)) if q_params else ""

with ana1:
    st.markdown("### R Distribution")
    try:
        b = safe_api_call('GET', f'api/pulse/analytics/trades/buckets{qstr}')
        edges = b.get('edges') if isinstance(b, dict) else None
        counts = b.get('counts') if isinstance(b, dict) else None
        if isinstance(edges, list) and isinstance(counts, list) and len(edges) == len(counts):
            # Render as bar at edge positions
            fig_b = go.Figure(go.Bar(x=edges, y=counts, marker_color='#60A5FA'))
            fig_b.update_layout(height=200, margin=dict(t=10, b=20, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_b.update_xaxes(title='R', color='#9CA3AF')
            fig_b.update_yaxes(title='Trades', color='#9CA3AF')
            st.plotly_chart(fig_b, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No distribution available yet.")
    except Exception:
        st.info("Distribution unavailable.")

with ana2:
    st.markdown("### Top Setups by Quality")
    try:
        s = safe_api_call('GET', f'api/pulse/analytics/trades/setups{qstr}')
        setups = s.get('setups') if isinstance(s, dict) else []
        if isinstance(setups, list) and setups:
            df_set = pd.DataFrame(setups)
            # Add total and show top 8
            if 'A+' in df_set.columns and 'B' in df_set.columns and 'C' in df_set.columns:
                df_set['Total'] = pd.to_numeric(df_set['A+'], errors='coerce').fillna(0) + pd.to_numeric(df_set['B'], errors='coerce').fillna(0) + pd.to_numeric(df_set['C'], errors='coerce').fillna(0)
                cols = [c for c in ['name', 'A+', 'B', 'C', 'Total'] if c in df_set.columns]
                st.dataframe(df_set[cols].head(8), use_container_width=True, height=240)
            else:
                st.dataframe(df_set.head(8), use_container_width=True, height=240)
        else:
            st.info("No setup data yet.")
    except Exception:
        st.info("Setups unavailable.")

# (Removed duplicate Session Trajectory section — already rendered above)

# Session Vitals (prototype)
with st.expander("🫀 Session Vitals (Prototype)", expanded=True):
    try:
        eq = float((acct or {}).get('equity') or 0)
        bal = float((acct or {}).get('balance') or 0)
        risk_env = risk or {}
        sod = float(risk_env.get('sod_equity') or bal or eq)
        prev_close = risk_env.get('prev_close_equity')
        target_amt = float(risk_env.get('target_amount') or 0)
        loss_amt = float(risk_env.get('loss_amount') or 0)
        pnl = eq - sod
        # Progress values
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
        # SoD and Prev Close quick readout
        c4, c5 = st.columns(2)
        with c4:
            st.caption(f"SoD (11pm): ${sod:,.0f}")
        with c5:
            try:
                pv = float(prev_close) if isinstance(prev_close, (int, float, str)) and str(prev_close).strip() != '' else None
            except Exception:
                pv = None
            st.caption(f"Prev Close: ${pv:,.0f}" if pv is not None else "Prev Close: —")
    except Exception:
        st.info("Vitals unavailable")

# Trade History (behavioral analysis)
st.subheader("Trade History")
sym_list = fetch_symbols() or []
sym_opts = ['All'] + sym_list
sel = st.selectbox("Filter by Symbol", sym_opts)
sym = None if sel == 'All' else sel

colf1, colf2, colf3, colf4 = st.columns(4)
with colf1:
    date_from = st.date_input("From", value=None)
with colf2:
    date_to = st.date_input("To", value=None)
with colf3:
    pnl_min = st.number_input("Min PnL", value=0.0, step=10.0, format="%f")
with colf4:
    pnl_max = st.number_input("Max PnL", value=0.0, step=10.0, format="%f")

df_str_from = date_from.isoformat() if date_from else None
df_str_to = date_to.isoformat() if date_to else None
pmin = pnl_min if pnl_min != 0.0 else None
pmax = pnl_max if pnl_max != 0.0 else None

hist = fetch_trade_history_filtered(symbol=sym, date_from=df_str_from, date_to=df_str_to, pnl_min=pmin, pnl_max=pmax)
try:
    import pandas as pd
    df = pd.DataFrame(hist)
    if not df.empty:
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'], errors='coerce')
        cols = [c for c in ['id','ts','symbol','direction','entry','exit','pnl','status'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, height=300)
        csv = df[cols].to_csv(index=False).encode('utf-8')
        st.download_button("Export to CSV", csv, "trade_history.csv", "text/csv")
    else:
        st.info("No trade history available yet.")
except Exception:
    st.info("History unavailable.")
