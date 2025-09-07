import plotly.graph_objects as go


def _dom(r):
    return dict(x=[0.5 - r, 0.5 + r], y=[0.5 - r, 0.5 + r])


def make_behavioral_compass(
    *,
    discipline: float = 100.0,              # 0..100 (unipolar green; remainder shows red)
    patience_ratio: float = 0.0,            # -0.5..+0.5 (CCW amber if negative; CW blue if positive)
    efficiency: float = 50.0,               # 0..100 (unipolar cyan; faint if <50)
    conviction_hi_win: float = 0.0,         # 0..100 (top semicircle green)
    conviction_lo_loss: float = 0.0,        # 0..100 (bottom semicircle red)
    pnl_norm: float | None = None,          # -1..+1 (inner tiny dial)
    title: str = "Behavioral Compass",
    subtitle: str | None = None,
):
    fig = go.Figure()

    # Background circle
    fig.add_shape(type="circle", x0=0.06, y0=0.06, x1=0.94, y1=0.94,
                  line=dict(color="#1e2329", width=1), fillcolor="#0c0f13", layer="below")

    # R1: Discipline (outer, unipolar). Green fill; remainder shows danger red.
    disc = max(0.0, min(100.0, float(discipline or 0))) / 100.0
    fig.add_trace(go.Pie(values=[disc, 1.0 - disc], hole=0.66, rotation=270, sort=False,
                         marker=dict(colors=["#22C55E", "rgba(239,68,68,0.35)"]),
                         textinfo="none", showlegend=False, direction="clockwise", domain=_dom(0.48)))

    # R2: Patience (tempo, bipolar); CW=blue if calmer, CCW=amber if faster.
    p = max(-0.5, min(0.5, float(patience_ratio or 0)))
    p_mag = abs(p) / 0.5  # map to 0..1
    p_dir = "clockwise" if p >= 0 else "counterclockwise"
    p_col = "#3B82F6" if p >= 0 else "#FBBF24"
    fig.add_trace(go.Pie(values=[p_mag, 1.0 - p_mag], hole=0.76, rotation=270, sort=False,
                         marker=dict(colors=[p_col, "rgba(255,255,255,0.07)"]),
                         textinfo="none", showlegend=False, direction=p_dir, domain=_dom(0.39), opacity=0.80))

    # R3: Profit Efficiency (unipolar cyan). Faint if <50.
    eff = max(0.0, min(100.0, float(efficiency or 0))) / 100.0
    eff_opacity = 0.45 if eff < 0.5 else 0.95
    fig.add_trace(go.Pie(values=[eff, 1.0 - eff], hole=0.76, rotation=270, sort=False,
                         marker=dict(colors=["#22D3EE", "rgba(255,255,255,0.07)"]),
                         textinfo="none", showlegend=False, direction="clockwise", domain=_dom(0.32), opacity=eff_opacity))

    # R4: Conviction split (inner ring): top green (hi-confidence win rate), bottom red (low-confidence loss rate)
    hi = max(0.0, min(100.0, float(conviction_hi_win or 0))) / 100.0
    lo = max(0.0, min(100.0, float(conviction_lo_loss or 0))) / 100.0
    # Top half (180°) clockwise green
    fig.add_trace(go.Pie(values=[hi, 1.0 - hi, 1.0], hole=0.84, rotation=270, sort=False,
                         marker=dict(colors=["#22C55E", "rgba(255,255,255,0.07)", "rgba(0,0,0,0)"]),
                         textinfo="none", showlegend=False, direction="clockwise", domain=_dom(0.26)))
    # Bottom half (180°) counterclockwise red
    fig.add_trace(go.Pie(values=[lo, 1.0 - lo, 1.0], hole=0.84, rotation=90, sort=False,
                         marker=dict(colors=["#EF4444", "rgba(255,255,255,0.07)", "rgba(0,0,0,0)"]),
                         textinfo="none", showlegend=False, direction="counterclockwise", domain=_dom(0.26)))

    # Center P&L tiny dial
    if pnl_norm is not None:
        pn = max(-1.0, min(1.0, float(pnl_norm)))
        pn_mag = abs(pn)
        pn_dir = "clockwise" if pn >= 0 else "counterclockwise"
        pn_col = "#22C55E" if pn >= 0 else "#EF4444"
        fig.add_trace(go.Pie(values=[pn_mag, 1.0 - pn_mag], hole=0.92, rotation=270, sort=False,
                             marker=dict(colors=[pn_col, "rgba(255,255,255,0.03)"]),
                             textinfo="none", showlegend=False, direction=pn_dir, domain=_dom(0.20)))
        fig.add_annotation(x=0.5, y=0.50, text=f"{('+' if pn>=0 else '−')}{int(pn_mag*100)}%", showarrow=False,
                           font=dict(size=16, color="#e5e7eb"))

    # Titles
    fig.add_annotation(x=0.5, y=0.90, text=title, showarrow=False, font=dict(size=14, color="#9ca3af"))
    if subtitle:
        fig.add_annotation(x=0.5, y=0.85, text=subtitle, showarrow=False, font=dict(size=12, color="#9ca3af"))

    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0b0f13", plot_bgcolor="#0b0f13", height=420)
    return fig
