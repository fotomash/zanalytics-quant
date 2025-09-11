import plotly.graph_objects as go


def _domain_for_radius(center=(0.5, 0.5), radius=0.45):
    cx, cy = center
    return dict(x=[cx - radius, cx + radius], y=[cy - radius, cy + radius])


def _ring_trace(
    label,
    value,
    max_abs=1.0,
    radius=0.45,
    thickness=0.10,
    bipolar=False,
    color_pos="#22c55e",
    color_neg="#ef4444",
    bg="#111418",
    start_at_12=True,
):
    """value in [0, max] for unipolar; in [-max_abs, +max_abs] for bipolar."""
    hole = max(0.0, 1.0 - (thickness / radius))
    dom = _domain_for_radius(radius=radius)

    if bipolar:
        direction = "clockwise" if (value or 0) >= 0 else "counterclockwise"
        color = color_pos if (value or 0) >= 0 else color_neg
        mag = min(abs(value or 0.0) / max_abs, 1.0)
        vals = [mag, 1.0 - mag]
    else:
        direction = "clockwise"
        color = color_pos
        mag = min(max(value or 0.0, 0.0) / max_abs, 1.0)
        vals = [mag, 1.0 - mag]

    return go.Pie(
        values=vals,
        hole=hole,
        direction=direction,
        rotation=-90 if start_at_12 else 0,
        textinfo="none",
        sort=False,
        marker=dict(colors=[color, bg]),
        showlegend=False,
        domain=dom,
        hoverinfo="skip",
        name=label,
    )


def make_behavioral_mirror(
    *,
    patience_ratio=-0.18,  # -0.5..+0.5 relative to baseline (negative = faster)
    discipline=82,  # 0..100
    conviction=61,  # 0..100
    efficiency=47,  # 0..100
    pnl=0.35,  # -1..+1 vs daily limit/target
    title="Behavioral Mirror",
    equity_text="Equity $0",
):
    fig = go.Figure()

    # Background disc (subtle)
    fig.add_shape(
        type="circle",
        x0=0.05,
        y0=0.05,
        x1=0.95,
        y1=0.95,
        line=dict(color="#1e2329", width=1),
        fillcolor="#0c0f13",
        layer="below",
    )

    # Rings: outer → inner
    fig.add_trace(
        _ring_trace(
            "Patience",
            patience_ratio,
            max_abs=0.5,
            radius=0.47,
            thickness=0.07,
            bipolar=True,
        )
    )
    fig.add_trace(
        _ring_trace(
            "Discipline",
            discipline,
            max_abs=100,
            radius=0.38,
            thickness=0.07,
            bipolar=False,
            color_pos="#60a5fa",
        )
    )
    fig.add_trace(
        _ring_trace(
            "Conviction",
            conviction,
            max_abs=100,
            radius=0.30,
            thickness=0.07,
            bipolar=False,
            color_pos="#a78bfa",
        )
    )
    fig.add_trace(
        _ring_trace(
            "Efficiency",
            efficiency,
            max_abs=100,
            radius=0.22,
            thickness=0.07,
            bipolar=False,
            color_pos="#f59e0b",
        )
    )

    # Center P&L dial as a thin ring
    fig.add_trace(
        _ring_trace(
            "PnL",
            pnl,
            max_abs=1.0,
            radius=0.14,
            thickness=0.06,
            bipolar=True,
            color_pos="#22c55e",
            color_neg="#ef4444",
        )
    )

    # Center annotations
    pnl_pct = int(abs(pnl or 0) * 100)
    sign = "+" if (pnl or 0) >= 0 else "−"
    fig.add_annotation(
        x=0.5,
        y=0.56,
        text=f"{sign}{pnl_pct}%",
        showarrow=False,
        font=dict(size=22, color="#e5e7eb"),
    )
    fig.add_annotation(
        x=0.5,
        y=0.47,
        text="of daily bound",
        showarrow=False,
        font=dict(size=12, color="#9ca3af"),
    )
    fig.add_annotation(
        x=0.5,
        y=0.86,
        text=title,
        showarrow=False,
        font=dict(size=14, color="#9ca3af"),
    )
    fig.add_annotation(
        x=0.5,
        y=0.12,
        text=equity_text,
        showarrow=False,
        font=dict(size=12, color="#9ca3af"),
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0b0f13",
        plot_bgcolor="#0b0f13",
        height=420,
    )
    return fig

