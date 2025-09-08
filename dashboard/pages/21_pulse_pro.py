"""
Zanalytics Pulse — Pro (React-style layout)
Live data wired to Pulse API, styled after the provided React template.
"""
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.ui_concentric import (
    concentric_ring,
    donut_session_vitals,
    donut_system_overview,
)
from dashboard.utils.streamlit_api import (
    safe_api_call,
    start_whisper_sse,
    drain_whisper_sse,
    render_status_row,
    get_sse_status,
    post_whisper_ack,
    post_whisper_act,
    fetch_symbols,
)
from dashboard.utils.plotly_gates import gate_donut, confluence_donut


# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse — Pro",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Subtle gradient/glass look
st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(1200px 600px at 10% 10%, rgba(29,78,216,0.08) 0%, rgba(15,23,42,0.0) 60%),
                        radial-gradient(800px 400px at 90% 0%, rgba(6,182,212,0.08) 0%, rgba(15,23,42,0.0) 60%),
                        linear-gradient(135deg, #0B1220 0%, #111827 100%);
        }
        .glass { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; }
        .section-title { color: #9CA3AF; font-size: 0.9rem; margin-bottom: 6px; }
        .metric-label { font-size: 0.75rem; color: #9CA3AF; text-transform: uppercase; }
        .metric-main { font-size: 1.25rem; font-weight: 700; color: #E5E7EB; }
        .scroll-thin::-webkit-scrollbar { width: 6px; }
        .scroll-thin::-webkit-scrollbar-track { background: #1F2937; border-radius: 3px; }
        .scroll-thin::-webkit-scrollbar-thumb { background: #4B5563; border-radius: 3px; }
        .pill { padding: 6px 10px; border-radius: 10px; font-size: 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Live API pulls ------------------------------------------------------------
mini = safe_api_call("GET", "api/v1/market/mini")
mirror = safe_api_call("GET", "api/v1/mirror/state")
acct = safe_api_call("GET", "api/v1/account/info")
risk = safe_api_call("GET", "api/v1/account/risk")
equity_series = safe_api_call("GET", "api/v1/feed/equity/series")
whispers_resp = safe_api_call("GET", "api/pulse/whispers")


# --- Header -------------------------------------------------------------------
st.markdown(
    """
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <div>
        <div style="font-size:28px;font-weight:800; background: linear-gradient(90deg, #60A5FA, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
          Zanalytics Pulse
        </div>
      </div>
      <div style="color:#9CA3AF;font-size:12px;">
        System Status · See below · Last Update: <span id="time_now">—</span>
      </div>
    </div>
    <script>document.getElementById('time_now')?.innerText = new Date().toLocaleTimeString();</script>
    """,
    unsafe_allow_html=True,
)

# Market conditions (VIX/DXY/regime) with tiny sparklines
vix = (mini.get("vix") or {}) if isinstance(mini, dict) else {}
dxy = (mini.get("dxy") or {}) if isinstance(mini, dict) else {}
regime = (mini.get("regime") if isinstance(mini, dict) else None) or "Neutral"

def _series(obj):
    try:
        s = obj.get("series") if isinstance(obj, dict) else []
        return list(s) if isinstance(s, list) else []
    except Exception:
        return []

vix_series = _series(vix)
dxy_series = _series(dxy)

hc1, hc2, hc3 = st.columns([1, 1, 1])
with hc1:
    st.caption("VIX")
    st.markdown(f"<div class='metric-main'>{float(vix.get('value') or 0.0):.2f}</div>", unsafe_allow_html=True)
    try:
        if vix_series:
            xs = list(range(len(vix_series)))
            fig = go.Figure(go.Scatter(x=xs, y=vix_series, mode="lines", line=dict(color="#22C55E", width=2)))
            fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass
with hc2:
    st.caption("DXY")
    st.markdown(f"<div class='metric-main'>{float(dxy.get('value') or 0.0):.2f}</div>", unsafe_allow_html=True)
    try:
        if dxy_series:
            xs = list(range(len(dxy_series)))
            fig = go.Figure(go.Scatter(x=xs, y=dxy_series, mode="lines", line=dict(color="#3B82F6", width=2)))
            fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass
with hc3:
    color = {"Risk-On": "#22C55E", "Risk-Off": "#EF4444"}.get(regime, "#FBBF24")
    st.markdown(
        f"<div class='pill' style='display:inline-block;border:1px solid rgba(255,255,255,0.08);background:{color}22;color:{color}'>Regime: {regime}</div>",
        unsafe_allow_html=True,
    )

render_status_row()
st.divider()


# --- Grid: Left (trading status), Center (donuts), Right (Whisperer) ---------
col_left, col_center, col_right = st.columns([1.2, 2.0, 1.2])

# LEFT PANEL — Trading Status
with col_left:
    st.markdown("#### Trading Status")
    bal = float((acct or {}).get("balance") or 0.0)
    eq = float((acct or {}).get("equity") or 0.0)
    sod = float((risk or {}).get("sod_equity") or bal or eq)
    pnl = eq - sod
    targ = float((risk or {}).get("target_amount") or 0.0)
    loss = float((risk or {}).get("loss_amount") or 0.0)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Balance</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-main'>${bal:,.0f}</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label' style='margin-top:8px'>Equity</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-main'>${eq:,.0f}</div>", unsafe_allow_html=True)
    pnl_color = "#22C55E" if pnl >= 0 else "#EF4444"
    st.markdown("<div class='metric-label' style='margin-top:8px'>P&L</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-main' style='color:{pnl_color}'>${pnl:+,.2f}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:rgba(255,255,255,0.08)'>", unsafe_allow_html=True)
    st.caption("Session Limits")
    st.markdown(f"<div style='color:#9CA3AF;font-size:12px'>Start: ${sod:,.0f}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#9CA3AF;font-size:12px'>Target: <span style='color:#22C55E'>+${targ:,.0f}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#9CA3AF;font-size:12px'>Daily Limit: <span style='color:#EF4444'>-${loss:,.0f}</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Pattern Watch (simple, uses placeholders until a feed exists)
    st.markdown("#### 🎯 Pattern Watch")
    for label, status, col in [
        ("Revenge", "OK", "#22C55E"),
        ("FOMO", "OK", "#22C55E"),
        ("Fear (cut winners)", "OK", "#22C55E"),
    ]:
        st.markdown(
            f"<div class='glass' style='border-left:3px solid {col}'>"
            f"<span style='color:{col}'>{label}: {status}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# CENTER — Donuts and Discipline Posture
with col_center:
    c1, c2 = st.columns(2)
    # Session Vitals donut (outer: hard deck, middle: daily DD, inner: P&L progress)
    with c1:
        try:
            baseline = float((risk or {}).get("baseline_equity") or bal or eq)
            target_amt = float((risk or {}).get("target_amount") or 0.0)
            loss_amt = float((risk or {}).get("loss_amount") or 0.0)
            st.markdown("##### Session Vitals")
            fig = donut_session_vitals(
                equity_usd=eq,
                sod_equity_usd=sod,
                baseline_equity_usd=baseline,
                daily_profit_pct=float((risk or {}).get("target_pct") or 0.0),
                daily_risk_pct=float((risk or {}).get("loss_pct") or 0.0),
                target_amount_usd=target_amt,
                loss_amount_usd=loss_amt,
                max_total_dd_pct=float((risk or {}).get("max_total_dd_pct") or 10.0),
                since_inception_pct=None,
                size=(260, 260),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("Outer: Hard Deck · Middle: Daily DD · Inner: P&L")
            # SoD and previous close equity readouts
            prev_close = (risk or {}).get("prev_close_equity")
            try:
                prev_close_f = float(prev_close) if isinstance(prev_close, (int, float, str)) and str(prev_close).strip() != '' else None
            except Exception:
                prev_close_f = None
            cso1, cso2 = st.columns(2)
            with cso1:
                st.caption(f"SoD (11pm): ${sod:,.0f}")
            with cso2:
                st.caption(f"Prev Close: ${prev_close_f:,.0f}" if prev_close_f is not None else "Prev Close: —")
        except Exception:
            st.info("Session vitals unavailable")

    # Behavioral Compass donut (system overview)
    with c2:
        try:
            # Exposure as 0..1
            exp_pct = (risk or {}).get("exposure_pct")
            if isinstance(exp_pct, (int, float)) and exp_pct > 1:
                exp_pct = exp_pct / 100.0
            exp_frac = float(exp_pct or 0.0)

            # Daily PnL normalized to ±1
            pnl_norm = 0.0
            try:
                if target_amt and pnl >= 0:
                    pnl_norm = min(1.0, pnl / target_amt)
                elif loss_amt and pnl < 0:
                    pnl_norm = -min(1.0, abs(pnl) / loss_amt)
            except Exception:
                pnl_norm = 0.0

            # Risk used fraction (0..1) of daily DD consumed
            risk_used = 0.0
            try:
                if eq < sod and loss_amt > 0:
                    risk_used = max(0.0, min(1.0, (sod - eq) / loss_amt))
            except Exception:
                risk_used = 0.0

            # Patience ratio tolerant conversion
            pr_raw = (mirror or {}).get("patience_ratio")
            if pr_raw is None:
                p = (mirror or {}).get("patience")
                try:
                    pr = float(p)
                    pr = (pr / 100.0) - 0.5
                except Exception:
                    pr = 0.0
            else:
                try:
                    pr = float(pr_raw)
                except Exception:
                    pr = 0.0

            st.markdown("##### Behavioral Compass")
            # Use system overview donut as a compact compass
            fig2 = donut_system_overview(
                equity_usd=eq,
                pnl_day_norm=pnl_norm,
                pnl_since_inception_pct=None,
                risk_used_pct=risk_used,
                exposure_pct=exp_frac,
                discipline_score=float((mirror or {}).get("discipline") or 0.0),
                patience_ratio=pr,
                # Anchor ticks: +1.0 at target, -1.0 at loss cap
                daily_target_norm=(1.0 if target_amt else None),
                daily_loss_norm=(-1.0 if loss_amt else None),
                target_amount=target_amt,
                loss_amount=loss_amt,
                size=(260, 260),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            # Quick readout lines
            cols = st.columns(2)
            with cols[0]:
                st.caption(f"Discipline: {float((mirror or {}).get('discipline') or 0):.0f}%")
                st.caption(f"Patience: {float((mirror or {}).get('patience') or 0):.0f}%")
            with cols[1]:
                st.caption(f"Efficiency: {float((mirror or {}).get('efficiency') or 0):.0f}%")
                st.caption(f"Conviction: {float((mirror or {}).get('conviction') or 0):.0f}%")
            # Additional 4-ring behavioral donut (discipline, patience, efficiency, conviction)
            def _val_pct(key: str, default=0.0) -> float:
                try:
                    v = (mirror or {}).get(key, default)
                    x = float(v)
                    if 0.0 <= x <= 1.0:
                        x *= 100.0
                    return max(0.0, min(100.0, x))
                except Exception:
                    return float(default)
            m = [
                {"name": "Discipline", "value": _val_pct("discipline"), "color": "#22C55E"},
                {"name": "Patience",   "value": _val_pct("patience"),   "color": "#3B82F6"},
                {"name": "Efficiency", "value": _val_pct("efficiency"), "color": "#06B6D4"},
                {"name": "Conviction", "value": _val_pct("conviction"), "color": "#8B5CF6"},
            ]
            sizes = [1.00, 0.82, 0.64, 0.46]
            band_px_ratio = 0.16
            track_color = "rgba(31,41,55,0.30)"
            start_at_noon = 90
            fig4 = go.Figure()
            for i, metric in enumerate(m):
                s = sizes[i]
                off = (1.0 - s) / 2.0
                hole = max(0.0, min(0.95, 1.0 - band_px_ratio))
                # track
                fig4.add_trace(go.Pie(values=[100], labels=[""], hole=hole, rotation=start_at_noon, direction="clockwise",
                                      marker=dict(colors=[track_color]), textinfo="none", showlegend=False, sort=False,
                                      domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off])))
                val = max(0.0, min(100.0, float(metric["value"])))
                # arc
                fig4.add_trace(go.Pie(values=[val, 100 - val], labels=[metric["name"], ""], hole=hole, rotation=start_at_noon,
                                      direction="clockwise", marker=dict(colors=[metric["color"], "rgba(0,0,0,0)"]),
                                      textinfo="none", hovertemplate=f"{metric['name']}: %{{percent}}<extra></extra>", showlegend=False,
                                      sort=False, domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off])))
            overall = int(sum(mm["value"] for mm in m) / 4.0)
            fig4.add_annotation(text=f"<b>{overall}%</b><br>Overall", x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#ffffff"))
            fig4.update_layout(height=260, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
        except Exception:
            st.info("Behavioral compass unavailable")

    # Discipline Posture (last 10 trades)
    st.markdown("##### 📊 Discipline Posture")
    dsum = safe_api_call("GET", "api/v1/discipline/summary")
    history = []
    if isinstance(dsum, dict) and isinstance(dsum.get("seven_day"), list) and dsum["seven_day"]:
        try:
            history = [int(x.get("score") or 0) for x in dsum["seven_day"]][-10:]
        except Exception:
            history = []
    if not history:
        history = [78, 82, 75, 88, 92, 85, 79, 83, 87, 90]
    colors = ["#22C55E" if d > 80 else "#FBBF24" if d > 60 else "#EF4444" for d in history]
    fig_d = go.Figure(go.Bar(x=list(range(1, 11)), y=history, marker_color=colors, text=[f"{d}%" for d in history], textposition="outside", textfont=dict(color="#9CA3AF", size=10)))
    fig_d.update_layout(height=160, margin=dict(t=10, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig_d.update_xaxes(title="Last 10 Trades", color="#9CA3AF", showgrid=False)
    fig_d.update_yaxes(range=[0, 100], showgrid=True, gridcolor="rgba(75,85,99,0.2)", color="#9CA3AF")
    st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})


# RIGHT — Whisperer
with col_right:
    status = get_sse_status()
    badge_col = "#10B981" if status == "connected" else ("#F59E0B" if status not in ("idle", "disconnected") else "#EF4444")
    st.markdown(f"#### 🤖 The Whisperer <span style='font-size:12px;color:{badge_col};margin-left:6px'>[{status}]</span>", unsafe_allow_html=True)
    start_whisper_sse()
    sse_items = drain_whisper_sse()
    whispers_raw = whispers_resp.get("whispers") if isinstance(whispers_resp, dict) else []
    if sse_items:
        whispers_raw = (whispers_raw or []) + sse_items
    items = []
    latest_slice = list(reversed((whispers_raw or [])[-25:]))
    for w in latest_slice:
        ts = w.get("ts")
        try:
            tdisp = datetime.fromtimestamp(float(ts)).strftime("%H:%M:%S") if ts else ""
        except Exception:
            tdisp = ""
        items.append({
            "time": tdisp or datetime.now().strftime("%H:%M:%S"),
            "type": (w.get("severity") or "insight"),
            "message": w.get("message") or "",
        })
    box = st.container()
    with box:
        html = ["<div class='scroll-thin' style='max-height:400px; overflow:auto'>"]
        for it in items:
            col = {"insight": "#3B82F6", "warning": "#FBBF24", "success": "#22C55E", "alert": "#EF4444"}.get(it["type"], "#3B82F6")
            icon = {"insight": "💡", "warning": "⚠️", "success": "✅", "alert": "🚨"}.get(it["type"], "💬")
            html.append(
                f"<div class='glass' style='border-left:3px solid {col}; margin:6px 0'>"
                f"<div style='display:flex;align-items:start;'>"
                f"<span style='font-size:1.2em;margin-right:8px'>{icon}</span>"
                f"<div style='flex:1'><div style='color:#6B7280;font-size:0.75em'>{it['time']}</div>"
                f"<div style='color:#E5E7EB;margin-top:4px'>{it['message']}</div></div></div></div>"
            )
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)

    # Quick Actions (Ack/Act) similar to page 04
    st.markdown("##### Quick Actions")
    if latest_slice:
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
        sel = st.selectbox("Select whisper", labels, index=0, key="ppro_sel_whisper")
        sel_w = options[labels.index(sel)][1]
        c1, c2 = st.columns(2)
        with c1:
            reason = st.text_input("Ack reason", value="", placeholder="optional", key="ppro_ack_reason")
            if st.button("✅ Acknowledge", use_container_width=True, key="ppro_ack_btn"):
                res = post_whisper_ack(sel_w.get("id"), reason or None)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Acknowledged")
                else:
                    st.error(f"Ack failed: {res}")
        with c2:
            acts = sel_w.get('actions') or []
            act_labels = [a.get('label') or a.get('action') for a in acts] or ["act_trail_50", "act_move_sl_be", "act_size_down"]
            act_values = [a.get('action') for a in acts] or act_labels
            act_choice = st.selectbox("Action", act_labels, index=0, key="ppro_act_sel")
            act_value = act_values[act_labels.index(act_choice)]
            if st.button("🚀 Act", use_container_width=True, key="ppro_act_btn"):
                res = post_whisper_act(sel_w.get("id"), act_value)
                if isinstance(res, dict) and res.get('ok'):
                    st.success("Action sent")
                else:
                    st.error(f"Act failed: {res}")
    else:
        st.info("No whispers yet.")


# --- Bottom strip --------------------------------------------------------------
st.divider()

# Analytics filters (applies to panels below)
flt1, flt2, flt3 = st.columns(3)
with flt1:
    try:
        _syms = fetch_symbols() or []
    except Exception:
        _syms = []
    _sym_opts = ['All'] + _syms
    _sym_sel = st.selectbox('Symbol', _sym_opts, index=0, key='ppro_sym')
    _sym = None if _sym_sel == 'All' else _sym_sel
with flt2:
    _dfrom = st.date_input('From', value=None, key='ppro_from')
with flt3:
    _dto = st.date_input('To', value=None, key='ppro_to')

_df_str_from = _dfrom.isoformat() if _dfrom else None
_df_str_to = _dto.isoformat() if _dto else None
_q_params = []
if _sym:
    _q_params.append(f'symbol={_sym}')
if _df_str_from:
    _q_params.append(f'date_from={_df_str_from}')
if _df_str_to:
    _q_params.append(f'date_to={_df_str_to}')
_qstr = ('?' + '&'.join(_q_params)) if _q_params else ''

bc1, bc2, bc3 = st.columns(3)
with bc1:
    st.markdown("#### Trade Quality Distribution")
    q = safe_api_call('GET', f'api/pulse/analytics/trades/quality{_qstr}')
    labels = q.get('labels') if isinstance(q, dict) else None
    counts = q.get('counts') if isinstance(q, dict) else None
    if not (isinstance(labels, list) and isinstance(counts, list) and len(labels) == len(counts)):
        labels, counts = ["A+", "B", "C"], [0, 0, 0]
    colors = ["#22C55E", "#FBBF24", "#EF4444"][:len(labels)]
    fig_q = go.Figure(go.Bar(x=labels, y=counts, marker_color=colors, text=counts, textposition="outside"))
    fig_q.update_layout(height=150, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_q, use_container_width=True, config={"displayModeBar": False})
with bc2:
    st.markdown("#### Session Momentum")
    momentum = float((mirror or {}).get("momentum") or 0.0)
    st.metric("Positive Momentum", f"{momentum:.0f}%")
    try:
        st.progress(max(0.0, min(1.0, momentum/100.0)))
    except Exception:
        st.progress(0.0)
    st.caption("Maintaining discipline")
    # Efficiency (captured vs potential)
    try:
        eff = safe_api_call('GET', f'api/pulse/analytics/trades/efficiency{_qstr}')
        pct = eff.get('captured_vs_potential_pct') if isinstance(eff, dict) else None
        if isinstance(pct, (int, float)):
            v = float(pct)
            st.metric("Captured vs Potential", f"{v*100:.0f}%")
            st.progress(max(0.0, min(1.0, v)))
    except Exception:
        pass
with bc3:
    st.markdown("#### Risk Management")
    try:
        summ = safe_api_call('GET', f'api/pulse/analytics/trades/summary{_qstr}')
        ar = summ.get('avg_r') if isinstance(summ, dict) else None
        if isinstance(ar, (int, float)):
            st.metric("Avg Risk/Trade", f"{float(ar):.2f}R")
        else:
            st.metric("Avg Risk/Trade", "—")
    except Exception:
        st.metric("Avg Risk/Trade", "—")
    ep = (risk or {}).get('exposure_pct') if isinstance(risk, dict) else None
    if isinstance(ep, (int, float)):
        st.metric("Max Exposure", f"{(ep if ep>1 else ep*100):.1f}%")
    else:
        st.metric("Max Exposure", "—")

# Additional Analytics Row
st.divider()
ac1, ac2 = st.columns(2)
with ac1:
    st.markdown("#### R Distribution")
    try:
        b = safe_api_call('GET', f'api/pulse/analytics/trades/buckets{_qstr}')
        edges = b.get('edges') if isinstance(b, dict) else None
        counts = b.get('counts') if isinstance(b, dict) else None
        if isinstance(edges, list) and isinstance(counts, list) and len(edges) == len(counts):
            fig_b = go.Figure(go.Bar(x=edges, y=counts, marker_color='#60A5FA'))
            fig_b.update_layout(height=220, margin=dict(t=10, b=20, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_b.update_xaxes(title='R', color='#9CA3AF')
            fig_b.update_yaxes(title='Trades', color='#9CA3AF')
            st.plotly_chart(fig_b, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No distribution available yet.")
    except Exception:
        st.info("Distribution unavailable.")
with ac2:
    st.markdown("#### Top Setups by Quality")
    try:
        s = safe_api_call('GET', f'api/pulse/analytics/trades/setups{_qstr}')
        setups = s.get('setups') if isinstance(s, dict) else []
        if isinstance(setups, list) and setups:
            df_set = pd.DataFrame(setups)
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

# Gate Scores (Behavioral)
st.divider()
st.markdown("#### 🧭 Behavioral Gates")
try:
    gates_raw = {
        'Discipline': (mirror or {}).get('discipline'),
        'Patience': (mirror or {}).get('patience'),
        'Conviction': (mirror or {}).get('conviction'),
        'Efficiency': (mirror or {}).get('efficiency'),
    }
    # Normalize 0..1 to 0..100 if needed
    gates: dict[str, float] = {}
    for k, v in gates_raw.items():
        try:
            x = float(v)
            if 0.0 <= x <= 1.0:
                x *= 100.0
            gates[k] = max(0.0, min(100.0, x))
        except Exception:
            gates[k] = 0.0
    # Simple subtitles based on current posture
    subs: dict[str, str | None] = {
        'Discipline': "Watch impulsive behavior" if gates['Discipline'] < 70 else None,
        'Patience': None,
        'Conviction': "Limit size on low confidence" if gates['Conviction'] < 70 else None,
        'Efficiency': "Improve capture vs potential" if gates['Efficiency'] < 70 else None,
    }
    # If mirror exposes patience_ratio, reflect tempo bias in subtitle
    try:
        pr = (mirror or {}).get('patience_ratio')
        if isinstance(pr, (int, float)):
            subs['Patience'] = 'Tempo high' if float(pr) < 0 else 'Tempo conservative'
    except Exception:
        pass

    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
    with gc1:
        st.plotly_chart(gate_donut(title='Discipline', score=gates['Discipline'], threshold=70, subtitle=subs['Discipline']), use_container_width=True, config={'displayModeBar': False})
    with gc2:
        st.plotly_chart(gate_donut(title='Patience', score=gates['Patience'], threshold=70, subtitle=subs['Patience']), use_container_width=True, config={'displayModeBar': False})
    with gc3:
        st.plotly_chart(gate_donut(title='Conviction', score=gates['Conviction'], threshold=70, subtitle=subs['Conviction']), use_container_width=True, config={'displayModeBar': False})
    with gc4:
        st.plotly_chart(gate_donut(title='Efficiency', score=gates['Efficiency'], threshold=70, subtitle=subs['Efficiency']), use_container_width=True, config={'displayModeBar': False})
    with gc5:
        st.plotly_chart(confluence_donut(title='Confluence', gates=gates), use_container_width=True, config={'displayModeBar': False})
except Exception:
    st.info("Behavioral gates unavailable")
