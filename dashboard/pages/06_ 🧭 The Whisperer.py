import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from dashboard.components.ui_concentric import donut_session_vitals
from dashboard.utils.streamlit_api import (
    safe_api_call,
    render_status_row,
    fetch_whispers,
    post_whisper_ack,
    post_whisper_act,
    get_trading_menu_options,
    start_whisper_sse,
    drain_whisper_sse,
    fetch_symbols,
    fetch_trade_history_filtered,
)

st.set_page_config(page_title="🧭 Whisperer Cockpit — Unified", page_icon="🧭", layout="wide")

st.markdown("# 🧭 Whisperer Cockpit — Unified")
st.caption("Behavioral compass • Session vitals • Trajectory • Pattern watch • Discipline posture • Whisper actions")
render_status_row()

# Start SSE for live whispers
start_whisper_sse()

def _fetch_mirror() -> dict:
    data = safe_api_call('GET', 'api/v1/mirror/state') or {}
    return data if isinstance(data, dict) else {}

def _fetch_account_risk() -> tuple[dict, dict]:
    info = safe_api_call('GET', 'api/v1/account/info') or {}
    risk = safe_api_call('GET', 'api/v1/account/risk') or {}
    return (info if isinstance(info, dict) else {}), (risk if isinstance(risk, dict) else {})

def _fetch_patterns() -> dict:
    data = safe_api_call('GET', 'api/v1/behavioral/patterns') or {}
    return data if isinstance(data, dict) else {}

def _fetch_equity_series() -> pd.DataFrame:
    data = safe_api_call('GET', 'api/v1/feed/equity/series') or {}
    pts = data.get('points') if isinstance(data, dict) else []
    if not isinstance(pts, list) or not pts:
        return pd.DataFrame()
    df = pd.DataFrame(pts)
    try:
        df['time'] = pd.to_datetime(df['ts'], errors='coerce')
    except Exception:
        df['time'] = pd.to_datetime('now')
    df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce')
    return df

# Fetch live inputs
mirror = _fetch_mirror()
acct, risk = _fetch_account_risk()
patterns = _fetch_patterns()
series = _fetch_equity_series()

colA, colB = st.columns([1.2, 1.2])
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
    fig.add_annotation(text=f"<b>{int(pd.Series([m['value'] for m in metrics]).mean())}%</b><br>Overall",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=20, color='white'))
    fig.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

with colB:
    st.subheader("🧩 Pattern Watch")
    chips = [
        ('Revenge Trading', patterns.get('revenge_trading') or {}),
        ('FOMO', patterns.get('fomo') or {}),
        ('Fear (Cut Winners)', patterns.get('fear_cut_winners') or {}),
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

# Session Vitals (full donut)
st.subheader("💰 Session Vitals")
try:
    eq = float(acct.get('equity') or 0)
    bal = float(acct.get('balance') or 0)
    sod = float(risk.get('sod_equity') or bal or eq)
    target_amt = risk.get('target_amount') if isinstance(risk.get('target_amount'), (int, float)) else None
    loss_amt = risk.get('loss_amount') if isinstance(risk.get('loss_amount'), (int, float)) else None
    daily_profit_pct = float(risk.get('daily_profit_pct') or 0.0)
    daily_risk_pct = float(risk.get('daily_risk_pct') or 0.0)
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
    st.caption("Outer: Hard Deck • Middle: Daily DD • Inner: P&L vs target/cap")
except Exception:
    st.info("Vitals unavailable")

# Session Trajectory
st.subheader("📈 Session Trajectory")
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

# Discipline Posture (awaiting a dedicated feed; placeholder structure)
st.subheader("📊 Discipline Posture")
try:
    # If historical discipline becomes available, render real bars; else info
    st.info("Awaiting discipline posture feed")
except Exception:
    pass

# Whisperer with Quick Actions
st.subheader("🤖 The Whisperer")
sse_items = drain_whisper_sse()
base_list = fetch_whispers()
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
    html = ["<div style='max-height:280px; overflow:auto'>"]
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
        if st.button("✅ Acknowledge", use_container_width=True, key="ack_btn_unified"):
            res = post_whisper_ack(sel_w.get("id"), reason or None)
            if isinstance(res, dict) and res.get('ok'):
                st.success("Acknowledged")
            else:
                st.error(f"Ack failed: {res}")
    with c2:
        acts = sel_w.get('actions') or []
        act_labels = [a.get('label') or a.get('action') for a in acts] or ["act_trail_50", "act_move_sl_be", "act_size_down"]
        act_values = [a.get('action') for a in acts] or act_labels
        act_choice = st.selectbox("Action", act_labels, index=0, key="act_sel_unified")
        act_value = act_values[act_labels.index(act_choice)]
        if st.button("🚀 Act", use_container_width=True, key="act_btn_unified"):
            res = post_whisper_act(sel_w.get("id"), act_value)
            if isinstance(res, dict) and res.get('ok'):
                st.success("Action sent")
            else:
                st.error(f"Act failed: {res}")

# Bottom tiles (placeholders tied to future feeds)
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
        used = risk.get('used_pct')
        exp = risk.get('exposure_pct')
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
        if not series.empty and len(series) > 2:
            df = series.tail(min(20, len(series)))
            inc = (df['pnl'].diff() > 0).mean()
            st.metric("Positive Momentum", f"{inc*100:.0f}%")
            st.caption("Last ~20 points")
        else:
            st.metric("Positive Momentum", "—")
            st.caption("Awaiting series")
    except Exception:
        st.metric("Positive Momentum", "—")

# Trade History (with filters)
st.subheader("🗂️ Trade History")
try:
    syms = fetch_symbols() or []
    c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
    with c1:
        sel_sym = st.selectbox("Symbol", ['All'] + syms)
        sym = None if sel_sym == 'All' else sel_sym
    with c2:
        dfrom = st.date_input("From", value=None, key='uh_from')
    with c3:
        dto = st.date_input("To", value=None, key='uh_to')
    with c4:
        pmin = st.number_input("Min PnL", value=0.0, step=10.0, format="%f", key='uh_pmin')
    with c5:
        pmax = st.number_input("Max PnL", value=0.0, step=10.0, format="%f", key='uh_pmax')
    data = fetch_trade_history_filtered(
        symbol=sym,
        date_from=(dfrom.isoformat() if dfrom else None),
        date_to=(dto.isoformat() if dto else None),
        pnl_min=(pmin if pmin != 0.0 else None),
        pnl_max=(pmax if pmax != 0.0 else None),
    )
    dfh = pd.DataFrame(data)
    if not dfh.empty:
        if 'ts' in dfh.columns:
            dfh['ts'] = pd.to_datetime(dfh['ts'], errors='coerce')
        cols = [c for c in ['id','ts','symbol','direction','entry','exit','pnl','status'] if c in dfh.columns]
        st.dataframe(dfh[cols], use_container_width=True, height=300)
        csv = dfh[cols].to_csv(index=False).encode('utf-8')
        st.download_button("Export CSV", csv, "trade_history.csv", "text/csv")
    else:
        st.info("No trades match filters.")
except Exception:
    st.info("History unavailable")
