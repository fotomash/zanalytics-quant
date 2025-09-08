import plotly.graph_objects as go
from typing import Dict, Any


def render_confluence_donut(gate_summary: Dict[str, Any], score: float) -> go.Figure:
    """
    Render a donut chart showing gate pass/fail status and overall score.

    gate_summary example:
        {"structure": "passed", "liquidity": "failed", "risk": "passed", ...}

    score: float between 0 and 1 (normalized confluence score).
    """
    labels = []
    values = []
    colors = []

    color_map = {
        "passed": "#22c55e",   # green
        "failed": "#ef4444",   # red
        "missing": "#9ca3af",  # gray
        "skipped": "#9ca3af",
        "partial": "#f59e0b",  # amber
    }

    for gate, status in gate_summary.items():
        if str(gate).startswith("score_"):
            continue
        labels.append(str(gate).replace("_gate", "").capitalize())
        values.append(1)
        colors.append(color_map.get(str(status).lower(), "#d1d5db"))

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors),
                direction="clockwise",
                textinfo="label",
                hoverinfo="label+percent",
                showlegend=False,
                sort=False,
            )
        ]
    )

    pct = max(0.0, min(1.0, float(score))) * 100.0
    fig.update_layout(
        margin=dict(t=8, b=8, l=8, r=8),
        height=220,
        annotations=[
            dict(text=f"{pct:.0f}%", x=0.5, y=0.5, font_size=20, font_color="#e5e7eb", showarrow=False)
        ],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


__all__ = ["render_confluence_donut"]

