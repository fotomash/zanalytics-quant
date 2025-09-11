from __future__ import annotations

import plotly.graph_objects as go
from dashboard.components.behavioral_compass import make_behavioral_compass


def _clamp01(x: float) -> float:
    try:
        x = float(x)
        if x != x:  # NaN
            return 0.0
        return max(0.0, min(1.0, x))
    except Exception:
        return 0.0


def fig_equity_donut(*, equity_usd: float, sod_equity_usd: float, prev_close_usd: float | None,
                     target_amount_usd: float | None, loss_amount_usd: float | None,
                     size: int = 280) -> go.Figure:
    """Bipolar equity donut. Clockwise (green) for profit vs target; counterclockwise (red) for loss vs cap.
    Shows previous session close as context in hover text.
    """
    eq = float(equity_usd or 0.0)
    sod = float(sod_equity_usd or 0.0)
    pnl = eq - sod
    targ = float(target_amount_usd) if isinstance(target_amount_usd, (int, float)) else 0.0
    loss = float(loss_amount_usd) if isinstance(loss_amount_usd, (int, float)) else 0.0

    if pnl >= 0 and targ > 0:
        val = _clamp01(pnl / targ)
        direction = 'clockwise'
        color = '#22C55E'
        hover = f"P&L +${pnl:,.0f} of +${targ:,.0f}"
    elif pnl < 0 and loss > 0:
        val = _clamp01(abs(pnl) / loss)
        direction = 'counterclockwise'
        color = '#EF4444'
        hover = f"P&L -${abs(pnl):,.0f} of -${loss:,.0f}"
    else:
        val = 0.0
        direction = 'clockwise'
        color = '#94A3B8'
        hover = "P&L 0"

    fig = go.Figure()
    fig.add_trace(go.Pie(values=[val, 1-val], hole=0.80, rotation=270, sort=False, direction=direction,
                         marker=dict(colors=[color, 'rgba(255,255,255,0.06)']), textinfo='none',
                         hoverinfo='text', hovertext=[hover, ''], showlegend=False))
    # Prev session marker (caption)
    if isinstance(prev_close_usd, (int, float)) and prev_close_usd:
        fig.update_layout(annotations=[dict(text=f"Prev close ${prev_close_usd:,.0f}",
                                            x=0.5, y=0.05, xref='paper', yref='paper',
                                            showarrow=False, font=dict(size=10, color='#9CA3AF'))])
    fig.update_layout(height=size, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


def fig_risk_donut(*, exposure_pct: float | None, pnl_usd: float, target_amount_usd: float | None,
                   loss_amount_usd: float | None, size: int = 280) -> go.Figure:
    """Risk/Exposure donut with two overlays: exposure (red) and P&L progress (green/red)."""
    exp = float(exposure_pct) if isinstance(exposure_pct, (int, float)) else 0.0
    exp = exp if exp <= 1.0 else exp / 100.0
    targ = float(target_amount_usd) if isinstance(target_amount_usd, (int, float)) else 0.0
    loss = float(loss_amount_usd) if isinstance(loss_amount_usd, (int, float)) else 0.0

    if pnl_usd >= 0 and targ > 0:
        prog = _clamp01(pnl_usd / targ)
        dirn = 'clockwise'
        pcol = '#22C55E'
        hov = f"Toward target: {prog*100:.0f}%"
    elif pnl_usd < 0 and loss > 0:
        prog = _clamp01(abs(pnl_usd) / loss)
        dirn = 'counterclockwise'
        pcol = '#EF4444'
        hov = f"Toward loss cap: {prog*100:.0f}%"
    else:
        prog = 0.0
        dirn = 'clockwise'
        pcol = '#94A3B8'
        hov = "P&L neutral"

    fig = go.Figure()
    # Exposure (red, inner)
    fig.add_trace(go.Pie(values=[_clamp01(exp), 1-_clamp01(exp)], hole=0.70, rotation=270, sort=False,
                         direction='clockwise', marker=dict(colors=['#EF4444', 'rgba(255,255,255,0.06)']),
                         textinfo='none', hoverinfo='text', hovertext=[f"Exposure {exp*100:.0f}%", ''], showlegend=False))
    # P&L progress overlay
    fig.add_trace(go.Pie(values=[prog, 1-prog], hole=0.84, rotation=270, sort=False, direction=dirn,
                         marker=dict(colors=[pcol, 'rgba(255,255,255,0.02)']), textinfo='none',
                         hoverinfo='text', hovertext=[hov, ''], showlegend=False))
    fig.update_layout(height=size, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


def fig_behavior_donut(*, discipline: float, patience: float, efficiency: float, size: int = 280) -> go.Figure:
    """Behavior donut with three rings (patience/discipline/efficiency)."""
    try:
        pat = _clamp01(float(patience)/100.0)
        dis = _clamp01(float(discipline)/100.0)
        eff = _clamp01(float(efficiency)/100.0)
    except Exception:
        pat = dis = eff = 0.0
    fig = go.Figure()
    # Patience (outer)
    fig.add_trace(go.Pie(values=[pat, 1-pat], hole=0.56, rotation=270, sort=False, direction='clockwise',
                         marker=dict(colors=['#22C55E', 'rgba(255,255,255,0.06)']), textinfo='none', showlegend=False))
    # Discipline (middle)
    fig.add_trace(go.Pie(values=[dis, 1-dis], hole=0.70, rotation=270, sort=False, direction='clockwise',
                         marker=dict(colors=['#3B82F6', 'rgba(255,255,255,0.06)']), textinfo='none', showlegend=False))
    # Efficiency (inner)
    fig.add_trace(go.Pie(values=[eff, 1-eff], hole=0.82, rotation=270, sort=False, direction='clockwise',
                         marker=dict(colors=['#06B6D4', 'rgba(255,255,255,0.06)']), textinfo='none', showlegend=False))
    fig.update_layout(height=size, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


def make_three_vitals(*,
                      equity_usd: float, sod_equity_usd: float, baseline_equity_usd: float,
                      target_amount_usd: float | None, loss_amount_usd: float | None,
                      exposure_pct: float | None,
                      prev_close_equity_usd: float | None,
                      discipline: float, patience: float, efficiency: float,
                      size: int = 280) -> tuple[go.Figure, go.Figure, go.Figure]:
    pnl = (equity_usd or 0.0) - (sod_equity_usd or 0.0)
    f1 = fig_equity_donut(equity_usd=equity_usd, sod_equity_usd=sod_equity_usd,
                          prev_close_usd=prev_close_equity_usd,
                          target_amount_usd=target_amount_usd, loss_amount_usd=loss_amount_usd,
                          size=size)
    f2 = fig_risk_donut(exposure_pct=exposure_pct, pnl_usd=pnl,
                        target_amount_usd=target_amount_usd, loss_amount_usd=loss_amount_usd,
                        size=size)
    f3 = fig_behavior_donut(discipline=discipline, patience=patience, efficiency=efficiency,
                            size=size)
    return f1, f2, f3


def fig_behavior_concentric_from_mirror(mirror: dict,
                                        pnl_norm: float | None = None,
                                        *,
                                        title: str = "Behavioral Compass",
                                        subtitle: str | None = "Keep red covered; tempo in check") -> go.Figure:
    """Convenience wrapper: build the concentric behavioral compass directly from a mirror dict.
    Accepts either 0..1 or 0..100 for numeric fields; tolerates missing keys.
    """
    def _g(d: dict, *keys, default=0.0):
        for k in keys:
            v = d.get(k)
            if v is None:
                continue
            try:
                x = float(v)
                if 0.0 <= x <= 1.0:
                    x *= 100.0
                return x
            except Exception:
                continue
        return float(default)

    mirror = mirror or {}
    # Patience: accept patience_ratio in [-0.5,0.5] or [-1,1], or patience in [0,100]
    pr_raw = mirror.get('patience_ratio')
    if pr_raw is None:
        pr_raw = mirror.get('patience', 50)
    try:
        prf = float(pr_raw)
        if -1.0 <= prf <= 1.0:
            patience_ratio = prf
        elif 0.0 <= prf <= 100.0:
            patience_ratio = (prf / 100.0) - 0.5
        else:
            patience_ratio = 0.0
    except Exception:
        patience_ratio = 0.0

    return make_behavioral_compass(
        discipline=_g(mirror, 'discipline'),
        patience_ratio=patience_ratio,
        efficiency=_g(mirror, 'efficiency'),
        conviction_hi_win=_g(mirror, 'conviction_hi_win', 'conviction'),
        conviction_lo_loss=_g(mirror, 'conviction_lo_loss', default=0.0),
        pnl_norm=pnl_norm,
        title=title,
        subtitle=subtitle,
    )
