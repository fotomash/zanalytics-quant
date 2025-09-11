from __future__ import annotations

import math
import graphviz
import plotly.graph_objects as go


def donut_chart(title: str, score: float, threshold: float = 70, subtitle: str | None = None) -> go.Figure:
    """Render a small donut with a threshold tick."""

    score = max(0.0, min(100.0, float(score)))
    frac = score / 100.0
    color = "#22C55E" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            values=[frac * 360, 360 - frac * 360],
            hole=0.75,
            sort=False,
            direction="clockwise",
            rotation=270,
            marker=dict(colors=[color, "rgba(148,163,184,0.28)"]),
            textinfo="none",
            showlegend=False,
        )
    )
    fig.add_annotation(
        text=f"<b>{title}</b><br>{score:.0f}%",
        x=0.5,
        y=0.55,
        showarrow=False,
        font=dict(size=14, color="#E5E7EB"),
    )
    if subtitle:
        fig.add_annotation(
            text=f"<span style='font-size:11px;color:#9CA3AF'>{subtitle}</span>",
            x=0.5,
            y=0.40,
            showarrow=False,
        )

    th_deg = max(0.0, min(360.0, threshold / 100.0 * 360.0))

    def ang2xy(a: float, r: float) -> tuple[float, float]:
        th = math.radians(90 - a)
        return 0.5 + r * math.cos(th), 0.5 + r * math.sin(th)

    x0, y0 = ang2xy(th_deg, 0.48)
    x1, y1 = ang2xy(th_deg, 0.50)
    fig.add_shape(
        type="line",
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        xref="paper",
        yref="paper",
        line=dict(color="#9CA3AF", width=2),
    )

    fig.update_layout(
        margin=dict(t=6, b=6, l=6, r=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=150,
        width=150,
    )
    return fig


def render_diagram() -> graphviz.Digraph:
    """Simple architecture diagram."""

    dot = graphviz.Digraph(format="svg")
    dot.node("User")
    dot.node("Whisperer", "LLM (Whisperer)")
    dot.node("Frontend")
    dot.node("Backend", "Backend/Kernel")
    dot.node("Adapter", "Data Adapter")
    dot.node("Broker")
    dot.edges(
        [
            ("User", "Whisperer"),
            ("Whisperer", "Frontend"),
            ("Frontend", "Backend"),
            ("Backend", "Adapter"),
            ("Adapter", "Broker"),
        ]
    )
    dot.edge("Whisperer", "Backend", style="dashed")
    return dot
