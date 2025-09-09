import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from dashboard.components.ui_concentric import donut_session_vitals, donut_equity
from dashboard.utils.confluence_visuals import render_confluence_donut
from dashboard.utils.plotly_donuts import bipolar_donut, oneway_donut, behavioral_score_from_mirror
from dashboard.utils.streamlit_api import (
    safe_api_call,
    render_status_row,
    inject_glass_css,
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

inject_glass_css()
st.markdown("# 🧭 Whisperer Cockpit — Unified")
st.caption("Behavioral compass • Session vitals • Trajectory • Pattern watch • Discipline posture • Whisper actions")
render_status_row()

# --- Symbol selector (multi-symbol ready) ---
try:
    _symbols = fetch_symbols() or []
except Exception:
    _symbols = []
if 'whisper_symbol' not in st.session_state:
    st.session_state['whisper_symbol'] = (_symbols[0] if _symbols else 'XAUUSD')
sel_sym = st.selectbox("Symbol", _symbols or ['XAUUSD'], index=(_symbols.index(st.session_state['whisper_symbol']) if (_symbols and st.session_state['whisper_symbol'] in _symbols) else 0))
st.session_state['whisper_symbol'] = sel_sym

# Agent Ops — Quick Checklist (price integrity)
with st.expander("Price Confirmation Checklist", expanded=False):
    st.markdown(
        "- Confirm latest price via `/api/v1/feed/bars-enriched` (preferred)\n"
        "- If primary feed is down, use Yahoo chart API (e.g., `XAUUSD=X`, `GC=F`)\n"
        "- Never state a price if no feed is reachable\n"
        "- When quoting, include instrument + timeframe + time (e.g., M15 close at 13:45Z)"
    )
    st.caption("See full guidance in Agent Ops → GPT Instructions below.")

# Agent Ops — GPT Instructions (inline reference)
with st.expander("Agent Ops — GPT Instructions", expanded=False):
    try:
        from pathlib import Path
        p = Path(__file__).resolve().parents[2] / "docs" / "custom_gpt_instructions.md"
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        if text:
            st.markdown(text)
        else:
            st.info("Instructions file not found: docs/custom_gpt_instructions.md")
    except Exception:
        st.info("Unable to load instructions.")

# Pulse Confidence (default symbol) + donut snapshot
try:
    syms = fetch_symbols() or []
    sym0 = st.session_state.get('whisper_symbol') or (syms[0] if syms else 'XAUUSD')
    # Build query inline because safe_api_call doesn't take params
    st_status = safe_api_call('GET', f'api/v1/feed/pulse-status?symbol={sym0}') or {}
    conf = st_status.get('confidence') if isinstance(st_status, dict) else None
    if isinstance(conf, (int, float)):
        pct = float(conf) * 100.0
        tone = '#22C55E' if pct >= 75 else ('#FBBF24' if pct >= 50 else '#EF4444')
        st.markdown(
            f"<div class='glass' style='display:inline-block;margin-top:6px;'>"
            f"<span style='color:#9CA3AF;margin-right:6px'>Pulse Confidence</span>"
            f"<span style='color:{tone};font-weight:700'>{pct:.1f}%</span>"
            f"<span style='color:#9CA3AF;margin-left:8px'>({sym0})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        # Donut: gate snapshot
        try:
            gate_order = ["context", "liquidity", "structure", "imbalance", "risk", "wyckoff"]
            summary = {}
            for g in gate_order:
                v = st_status.get(g)
                if v is None:
                    summary[g] = "missing"
                else:
                    summary[g] = "passed" if int(v) == 1 else "failed"
            fig_conf = render_confluence_donut(summary, float(conf))
            st.plotly_chart(fig_conf, use_container_width=True)
        except Exception:
            pass
except Exception:
    pass

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

# Session Vitals — unified equity donut with professional markers
st.subheader("💰 Session Vitals")

try:
    # Helper to pull inception/starting balances when available
    def _as_float(v, default=0.0):
        try:
            return float(v)
        except Exception:
            return float(default)
    inception = None
    # Prefer explicit inception keys if backend provides them
    # Fallbacks: account 'balance_initial' or risk 'prev_close_equity'
    try:
        inception = risk.get('inception_equity')
    except Exception:
        inception = None
    if inception is None:
        inception = acct.get('balance_initial') if isinstance(acct, dict) else None
    if inception is None:
        inception = risk.get('prev_close_equity') if isinstance(risk, dict) else None
    inception = _as_float(inception, None)

    # Pull account & risk
    eq = float(acct.get('equity') or 0.0)
    bal = float(acct.get('balance') or 0.0)
    sod = float(risk.get('sod_equity') or bal or eq)
    target_amt = float(risk.get('target_amount') or 0.0)
    loss_amt = float(risk.get('loss_amount') or 0.0)
    pnl_today = eq - sod
    exp_pct = risk.get('exposure_pct') or 0.0
    exp_ratio = float(exp_pct/100.0 if exp_pct > 1 else exp_pct)
    bhv_score = behavioral_score_from_mirror(mirror)
    bhv_ratio = bhv_score/100.0

    cV1, cV2, cV3 = st.columns(3)
    with cV1:
        # Equity donut with explicit SoD anchor and target/loss ticks
        fig_eq = bipolar_donut(
            title="Equity vs SoD (11pm UK)",
            value=pnl_today,
            pos_max=max(1.0, target_amt),
            neg_max=max(1.0, loss_amt),
            start_anchor="top",
            center_title=f"{eq:,.0f}",
            center_sub=f"{pnl_today:+,.0f} today",
        )
        # Add subtle tick markers for target/loss and zero-line (SoD)
        try:
            fig_eq.add_annotation(text="+Target", x=0.82, y=0.80, showarrow=False, font=dict(size=10, color="#9CA3AF"))
            fig_eq.add_annotation(text="-Loss",   x=0.18, y=0.20, showarrow=False, font=dict(size=10, color="#9CA3AF"))
            fig_eq.add_annotation(text="SoD",     x=0.50, y=0.96, showarrow=False, font=dict(size=10, color="#9CA3AF"))
        except Exception:
            pass
        st.plotly_chart(fig_eq, use_container_width=True)

        # Professional readouts under the donut
        r1, r2 = st.columns(2)
        with r1:
            st.metric("SoD Equity", f"${sod:,.0f}")
            if inception is not None:
                st.metric("Inception Equity", f"${inception:,.0f}")
        with r2:
            st.metric("Target (today)", f"+${target_amt:,.0f}" if target_amt > 0 else "—")
            st.metric("Loss Cap (today)", f"-${loss_amt:,.0f}" if loss_amt > 0 else "—")
        st.caption("Donut: outer=P&L vs target/loss • SoD=zero line • ticks at ±daily bounds")

    with cV2:
        st.plotly_chart(
            oneway_donut(
                title="Position Exposure",
                frac=exp_ratio,
                start_anchor="bottom",
                center_title=f"{exp_ratio*100:.0f}%",
                center_sub="of daily risk budget",
            ),
            use_container_width=True,
        )
    with cV3:
        st.plotly_chart(
            oneway_donut(
                title="Behavioral Posture",
                frac=bhv_ratio,
                start_anchor="top",
                center_title=f"{bhv_score:.0f}" if isinstance(bhv_score, (int, float)) else "—",
                center_sub="composite",
            ),
            use_container_width=True,
        )
except Exception:
    st.info("Vitals unavailable")

# Session Insights
st.markdown("### 🧠 Session Insights")
try:
    ins = []
    used = risk.get('used_pct')
    used_ratio = float(used/100.0 if (used is not None and used > 1) else (used or 0.0))
    dd_used = min(abs(min(pnl_today, 0.0)) / max(1.0, loss_amt), 1.0) if loss_amt else 0.0
    pos_used = min(max(pnl_today, 0.0) / max(1.0, target_amt), 1.0) if target_amt else 0.0

    if dd_used >= 0.8:
        ins.append(f"🚨 Drawdown used {dd_used*100:.0f}% of daily cap.")
    elif dd_used >= 0.5:
        ins.append(f"⚠️ Drawdown used {dd_used*100:.0f}% — tighten risk.")

    if used_ratio >= 0.8:
        ins.append(f"⚠️ Daily risk used {used_ratio*100:.0f}%. Consider scaling down.")
    elif exp_ratio >= 0.6:
        ins.append(f"🟡 Exposure {exp_ratio*100:.0f}% — keep size disciplined.")

    if pos_used >= 0.8:
        ins.append(f"✅ {pos_used*100:.0f}% toward target — protect profits.")
    if bhv_score and bhv_score < 60:
        ins.append("🧭 Behavioral < 60 — breathe, follow plan.")
    elif bhv_score and bhv_score >= 85:
        ins.append("🎯 Behavioral strong — stay selective.")

    if not ins:
        ins.append("✅ Stable posture. Follow checklist and wait for A‑setups.")
    st.markdown("\n".join(f"- {s}" for s in ins))
except Exception:
    st.info("Insights unavailable")

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
            df7 = pd.DataFrame(series7)
            if 'date' in df7 and 'score' in df7:
                df7['date'] = pd.to_datetime(df7['date'], errors='coerce')
                figD = go.Figure(go.Bar(x=df7['date'], y=df7['score'], marker_color=['#22C55E' if x>=70 else '#FBBF24' if x>=50 else '#EF4444' for x in df7['score']]))
                figD.update_layout(height=180, margin=dict(t=10,b=10,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(figD, use_container_width=True)
        else:
            st.caption("No history yet")
except Exception:
    st.info("Discipline summary unavailable")

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

# Agent Actions Menu (from whisperer_zanflow_master.yaml)
st.divider()
st.subheader("🧭 Agent Actions Menu")
try:
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).resolve().parents[2] / "docs" / "gpt_llm" / "whisperer_zanflow_pack" / "whisperer_zanflow_master.yaml"
    actions_list = []
    action_info = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        arr = data.get('actions_available') or []
        if isinstance(arr, list):
            actions_list = [str(x) for x in arr]
        bindings = data.get('action_bindings') or {}
        if isinstance(bindings, dict):
            for k, v in bindings.items():
                if isinstance(v, dict):
                    action_info[k] = v.get('description') or ''
    if actions_list:
        choice = st.selectbox("Available agent actions", actions_list)
        desc = action_info.get(choice) or '—'
        st.caption(desc)
    else:
        st.info("No actions_available found in master config.")
except Exception:
    st.info("Unable to load agent actions menu.")

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
    c0, c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1,1])
    with c0:
        from datetime import date, timedelta
        last_n = st.number_input("Last N days", min_value=0, max_value=365, value=0, step=1, help="0 = disabled; else overrides From date", key='uh_lastn')
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
    # Apply preset last N days if set
    df_str_from = (dfrom.isoformat() if dfrom else None)
    df_str_to = (dto.isoformat() if dto else None)
    if last_n and last_n > 0:
        try:
            df_str_from = (date.today() - timedelta(days=int(last_n))).isoformat()
        except Exception:
            pass

    data = fetch_trade_history_filtered(
        symbol=sym,
        date_from=df_str_from,
        date_to=df_str_to,
        pnl_min=(pmin if pmin != 0.0 else None),
        pnl_max=(pmax if pmax != 0.0 else None),
    )
    dfh = pd.DataFrame(data)
    if not dfh.empty:
        # Quick stats row
        try:
            pnl_series = pd.to_numeric(dfh.get('pnl'), errors='coerce').fillna(0.0)
            total = len(dfh)
            wins = int((pnl_series > 0).sum())
            winrate = (wins/total*100.0) if total else 0.0
            avg_pnl = float(pnl_series.mean()) if total else 0.0
            cst1, cst2, cst3 = st.columns(3)
            cst1.metric("Trades", f"{total}")
            cst2.metric("Win Rate", f"{winrate:.0f}%")
            cst3.metric("Avg PnL", f"${avg_pnl:,.2f}")
        except Exception:
            pass
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
