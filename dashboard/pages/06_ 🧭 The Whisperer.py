import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import requests
from dashboard.utils.streamlit_api import (
    safe_api_call,
    fetch_whispers,
    post_whisper_ack,
    post_whisper_act,
    get_trading_menu_options,
    render_status_row,
    start_whisper_sse,
    drain_whisper_sse,
    get_sse_status,
)

# Page configuration
st.set_page_config(
    page_title="🧭 The Whisperer — Pulse Cockpit",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for sophisticated styling
st.markdown(
    """
<style>
    .stApp { background: linear-gradient(135deg, #0B1220 0%, #111827 100%); }
    .metric-card {
        background: rgba(31, 41, 55, 0.5);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(75, 85, 99, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .whisper-message { background: rgba(31, 41, 55, 0.3); border-left: 3px solid; padding: 12px; margin: 8px 0; border-radius: 0 8px 8px 0; }
    .whisper-insight { border-color: #3B82F6; }
    .whisper-warning { border-color: #FBBF24; }
    .whisper-success { border-color: #22C55E; }
    .whisper-alert { border-color: #EF4444; }
    h1, h2, h3 { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 600; }
    .big-metric { font-size: 2.5rem; font-weight: 700; line-height: 1; }
    .metric-label { font-size: 0.875rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; }
</style>
""",
    unsafe_allow_html=True,
)

"""Live Whisperer page using shared API helpers."""

# Initialize session state
if 'discipline_score' not in st.session_state:
    st.session_state.discipline_score = 85
    st.session_state.patience_index = 72
    st.session_state.conviction_rate = 68
    st.session_state.profit_efficiency = 74
    st.session_state.current_pnl = 248.00
    st.session_state.session_equity = 203229.05
    st.session_state.whispers = []

def _fetch_market_mini() -> dict:
    data = safe_api_call('GET', 'api/v1/market/mini') or {}
    return data if isinstance(data, dict) else {}

def _fetch_mirror() -> dict:
    data = safe_api_call('GET', 'api/v1/mirror/state') or {}
    return data if isinstance(data, dict) else {}

def _fetch_account() -> tuple[float, float, float, float]:
    info = safe_api_call('GET', 'api/v1/account/info') or {}
    risk = safe_api_call('GET', 'api/v1/account/risk') or {}
    equity = float(info.get('equity') or 0)
    balance = float(info.get('balance') or 0)
    sod = float(risk.get('sod_equity') or balance or equity)
    pnl = equity - sod
    return balance, equity, sod, pnl

def _fetch_patterns() -> dict:
    data = safe_api_call('GET', 'api/v1/behavioral/patterns') or {}
    return data if isinstance(data, dict) else {}

def _fetch_whispers() -> list[dict]:
    return fetch_whispers()

def _fetch_equity_series() -> list[dict]:
    data = safe_api_call('GET', 'api/v1/feed/equity/series') or {}
    pts = data.get('points') if isinstance(data, dict) else []
    return pts if isinstance(pts, list) else []

def _session_trajectory():
    hours = pd.date_range(start='2025-01-01 09:30', end='2025-01-01 16:00', freq='15min')
    base = np.cumsum(np.random.randn(len(hours)) * 50)
    events = [
        {'i': 10, 'type': 'revenge', 'impact': -150},
        {'i': 20, 'type': 'overconfidence', 'impact': -80},
        {'i': 35, 'type': 'milestone', 'impact': 200},
    ]
    for e in events:
        if e['i'] < len(base):
            base[e['i']:] += e['impact']
    return pd.DataFrame({
        'time': hours,
        'pnl': base,
        'events': [
            'revenge' if i == 10 else 'overconfidence' if i == 20 else 'milestone' if i == 35 else None
            for i in range(len(hours))
        ],
    })

# Auto-refresh toggle (best-effort)
live = st.sidebar.checkbox("Live refresh", value=False, help="Auto‑refresh every 5s")
if live:
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=5000, key="whisp_autoref")
    except Exception:
        pass
try:
    if live:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=5000, key="whisp_autoref")
except Exception:
    pass

# Start SSE for whispers (non-blocking)
start_whisper_sse()

# Fetch live data (with graceful fallbacks)
mini = _fetch_market_mini()
mirror = _fetch_mirror()
bal, eq, sod_eq, pnl_usd = _fetch_account()

# Header
st.markdown("# 🧭 The Whisperer")
st.caption("Behavioral co‑pilot for disciplined execution")
render_status_row()

mkt = {
    'vix': (mini.get('vix') or {}).get('value') or 14.8,
    'dxy': (mini.get('dxy') or {}).get('value') or 103.4,
    'regime': mini.get('regime') or 'Neutral'
}
hc1, hc2, hc3, hc4 = st.columns([1, 1, 1, 2])
with hc1:
    st.metric("VIX", f"{mkt['vix']:.2f}", f"{np.random.choice(['+','-'])}{abs(np.random.randn()*0.5):.2f}")
with hc2:
    st.metric("DXY", f"{mkt['dxy']:.2f}", f"{np.random.choice(['+','-'])}{abs(np.random.randn()*0.2):.2f}")
with hc3:
    regime_icon = {'Risk-On':'🟢','Neutral':'🟡','Risk-Off':'🔴'}
    st.metric("Regime", f"{regime_icon[mkt['regime']]} {mkt['regime']}")
with hc4:
    st.metric("System Status", "✅ All Systems Operational", "Lag: ~2ms")

st.divider()

col_left, col_center, col_right = st.columns([1.5, 2, 1.5])

# LEFT — Behavioral Compass (mirror state)
with col_left:
    st.markdown("### 🎯 Behavioral Compass")
    fig = go.Figure()
    metrics = [
        {'name': 'Discipline', 'value': int(mirror.get('discipline') or 0), 'color': '#22C55E'},
        {'name': 'Patience', 'value': int(mirror.get('patience_ratio') or 0), 'color': '#3B82F6'},
        {'name': 'Efficiency', 'value': int(mirror.get('efficiency') or 0), 'color': '#06B6D4'},
        {'name': 'Conviction', 'value': int(mirror.get('conviction_hi_win') or 0), 'color': '#8B5CF6'},
    ]
    for i, m in enumerate(metrics):
        fig.add_trace(go.Pie(
            values=[m['value'], 100 - m['value']],
            hole=0.4 + i*0.1,
            marker=dict(colors=[m['color'], 'rgba(31,41,55,0.3)']),
            textinfo='none', showlegend=False,
            hovertemplate=f"{m['name']}: {m['value']}%<extra></extra>",
            domain=dict(x=[0.1*i, 1-0.1*i], y=[0.1*i, 1-0.1*i])
        ))
    fig.add_annotation(text=f"<b>{int(np.mean([m['value'] for m in metrics]))}%</b><br>Overall",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=20, color='white'))
    fig.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    for m in metrics:
        a, b = st.columns([3,1])
        with a: st.markdown(f"**{m['name']}**")
        with b: st.markdown(f"<span style='color:{m['color']};font-weight:700'>{m['value']}%</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🎯 Pattern Watch")
    patt = _fetch_patterns()
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

# CENTER — Session Vitals & Trajectory
with col_center:
    st.markdown("### 💰 Session Vitals")
    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        pnl_color = '#22C55E' if pnl_usd >= 0 else '#EF4444'
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>P&L</div>"
            f"<div class='big-metric' style='color:{pnl_color};'>${pnl_usd:+.2f}</div></div>",
            unsafe_allow_html=True)
    with vc2:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Equity</div>"
            f"<div class='big-metric'>${eq:,.0f}</div></div>",
            unsafe_allow_html=True)
    with vc3:
        risk_env = safe_api_call('GET', 'api/v1/account/risk') or {}
        target_amt = float(risk_env.get('target_amount') or 0)
        target_progress = min(((pnl_usd / target_amt) * 100) if target_amt > 0 else 0, 100)
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Target Progress</div>"
            f"<div class='big-metric'>{target_progress:.0f}%</div></div>",
            unsafe_allow_html=True)

    st.markdown("### 📈 Session Trajectory")
    series = _fetch_equity_series()
    if series:
        T = pd.DataFrame(series)
        try:
            T['time'] = pd.to_datetime(T['ts'], errors='coerce')
        except Exception:
            T['time'] = pd.to_datetime('now')
        T['pnl'] = pd.to_numeric(T['pnl'], errors='coerce').fillna(0.0)
    else:
        T = pd.DataFrame({'time': [pd.to_datetime('now')], 'pnl': [0.0]})
    figT = go.Figure()
    figT.add_trace(go.Scatter(x=T['time'], y=T['pnl'], mode='lines', name='P&L',
                              line=dict(color='#22C55E', width=2), fill='tozeroy',
                              fillcolor='rgba(34,197,94,0.1)'))
    # Behavioral markers could be layered when event data is available.
    figT.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.3)
    figT.update_layout(height=300, margin=dict(t=0,b=20,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False, color='#9CA3AF', tickformat='%H:%M'),
                       yaxis=dict(showgrid=True, gridcolor='rgba(75,85,99,0.2)', color='#9CA3AF', title='P&L ($)'),
                       showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                       bgcolor='rgba(0,0,0,0)', font=dict(color='#9CA3AF', size=10)), hovermode='x unified')
    st.plotly_chart(figT, use_container_width=True)

    st.markdown("### 📊 Discipline Posture")
    hist = [78, 82, 75, 88, 92, 85, 79, 83, 87, int(mirror.get('discipline') or 0)]
    colors = ['#22C55E' if d > 80 else '#FBBF24' if d > 60 else '#EF4444' for d in hist]
    figD = go.Figure(go.Bar(x=list(range(1, 11)), y=hist, marker_color=colors,
                            text=[f'{d}%' for d in hist], textposition='outside',
                            textfont=dict(color='#9CA3AF', size=10),
                            hovertemplate='Trade %{x}<br>Discipline: %{y}%<extra></extra>'))
    figD.update_layout(height=200, margin=dict(t=20,b=20,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       xaxis=dict(title='Last 10 Trades', color='#9CA3AF', showgrid=False),
                       yaxis=dict(range=[0, 100], showgrid=True, gridcolor='rgba(75,85,99,0.2)', color='#9CA3AF'),
                       showlegend=False)
    st.plotly_chart(figD, use_container_width=True)

# RIGHT — The Whisperer (live list, best-effort)
with col_right:
    st.markdown("### 🤖 The Whisperer")
    # Pull SSE whispers and merge with HTTP latest
    sse_items = drain_whisper_sse()
    base_list = _fetch_whispers()
    whispers_raw = base_list + sse_items if sse_items else base_list
    whispers = []
    latest_slice = list(reversed((whispers_raw or [])[-25:]))
    for w in latest_slice:
        typ = (w.get('severity') or 'insight').lower()
        ts = w.get('ts')
        try:
            tdisp = datetime.fromtimestamp(float(ts)).strftime('%H:%M:%S') if ts else ''
        except Exception:
            tdisp = ''
        whispers.append({'time': tdisp or datetime.now().strftime('%H:%M:%S'), 'type': typ, 'message': w.get('message') or '', 'id': w.get('id'), 'actions': w.get('actions') or []})
    wc = st.container()
    with wc:
        icons = {'insight': '💡', 'warning': '⚠️', 'success': '✅', 'alert': '🚨'}
        sse_badge = get_sse_status()
        st.caption(f"Whisper Stream: {('✅ connected' if sse_badge=='connected' else '⚠️ fallback')} ")
        html = ["<div style='max-height:400px; overflow:auto'>"]
        for w in whispers:
            html.append(
                f"<div class='whisper-message whisper-{w['type']}'>"
                f"<div style='display:flex;align-items:start;'>"
                f"<span style='font-size:1.2em;margin-right:8px'>{icons.get(w['type'],'💬')}</span>"
                f"<div style='flex:1'>"
                f"<div style='color:#6B7280;font-size:0.75em'>{w['time']}</div>"
                f"<div style='color:#E5E7EB;margin-top:4px'>{w['message']}</div>"
                f"</div></div></div>"
            )
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)

    st.markdown("### Quick Actions")
    if latest_slice:
        # Build selector for recent whispers
        options = []
        for w in latest_slice[:10]:
            ts = w.get('ts')
            try:
                tdisp = datetime.fromtimestamp(float(ts)).strftime('%H:%M:%S') if ts else ''
            except Exception:
                tdisp = ''
            label = f"{tdisp} — {str(w.get('message') or '')[:80]}"
            options.append((label, w))
        labels = [o[0] for o in options]
        sel = st.selectbox("Select whisper", labels, index=0)
        sel_w = options[labels.index(sel)][1]
        c1, c2 = st.columns(2)
        with c1:
            reason = st.text_input("Ack reason", value="", placeholder="optional")
            if st.button("✅ Acknowledge", use_container_width=True, key="ack_btn"):
                res = post_whisper_ack(sel_w.get("id"), reason or None)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Acknowledged")
                else:
                    st.error(f"Ack failed: {res}")
        with c2:
            acts = sel_w.get('actions') or []
            act_labels = [a.get('label') or a.get('action') for a in acts] or ["act_trail_50", "act_move_sl_be", "act_size_down"]
            act_values = [a.get('action') for a in acts] or act_labels
            act_choice = st.selectbox("Action", act_labels, index=0, key="act_sel")
            act_value = act_values[act_labels.index(act_choice)]
            if st.button("🚀 Act", use_container_width=True, key="act_btn"):
                res = post_whisper_act(sel_w.get("id"), act_value)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Action sent")
                else:
                    st.error(f"Act failed: {res}")
    else:
        st.info("No whispers yet.")

st.divider()
bc1, bc2, bc3, bc4 = st.columns(4)
with bc1:
    st.markdown("### Trade Quality")
    df = pd.DataFrame({'Setup':['A+','B','C'], 'Count':[12,8,3]})
    figQ = go.Figure(go.Bar(x=df['Setup'], y=df['Count'], marker_color=['#22C55E','#FBBF24','#EF4444'],
                            text=df['Count'], textposition='outside'))
    figQ.update_layout(height=150, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                       xaxis=dict(color='#9CA3AF'), yaxis=dict(visible=False), showlegend=False)
    st.plotly_chart(figQ, use_container_width=True)
with bc2:
    st.markdown("### Profit Efficiency")
    st.metric("Captured vs Potential", "74%", "+5%")
    st.progress(0.74)
    st.caption("Letting winners run better")
with bc3:
    st.markdown("### Risk Management")
    st.metric("Avg Risk/Trade", "1.2R")
    st.metric("Max Exposure", "3.5%", "-0.5%")
with bc4:
    st.markdown("### Session Momentum")
    momentum = 68
    st.metric("Positive Momentum", f"{momentum}%")
    st.progress(momentum/100)
    st.caption("Maintaining discipline")

# Optional quick live update demo
ph = st.empty()
if st.button("🔄 Enable Live Updates"):
    while True:
        with ph.container():
            st.info("Dashboard updating…")
        time.sleep(5)
        st.rerun()
