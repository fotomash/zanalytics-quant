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


def render_confluence_gates(scores: Dict[str, float], weights: Dict[str, float]) -> go.Figure:
    """Render weighted confluence gates as a donut chart.

    Parameters
    ----------
    scores:
        Mapping of gate name to numeric score (0-100).
    weights:
        Mapping of gate name to weight. Missing gates default to weight 0.

    Returns
    -------
    plotly.graph_objects.Figure
        Donut chart showing gate statuses and overall confluence score.
    """

    weights = weights or {}
    total_weight = sum(weights.values()) or 1.0
    total_score = sum(scores.get(gate, 0) * weight for gate, weight in weights.items()) / total_weight
    total_score = max(0.0, min(100.0, float(total_score)))

    gate_summary: Dict[str, Any] = {}
    for gate, score in scores.items():
        s = float(score or 0)
        if s >= 70:
            gate_summary[gate] = "passed"
        elif s >= 50:
            gate_summary[gate] = "partial"
        else:
            gate_summary[gate] = "failed"

    return render_confluence_donut(gate_summary, total_score / 100.0)


__all__ = ["render_confluence_donut", "render_confluence_gates"]

