import plotly.graph_objects as go
import numpy as np


def _band_color(x: float, green: str = "#22C55E", yellow: str = "#F59E0B", red: str = "#EF4444") -> str:
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return green if x <= 0.40 else yellow if x <= 0.75 else red


def bipolar_donut(
    title: str,
    value: float,
    pos_max: float,
    neg_max: float,
    start_anchor: str = "top",
    center_title: str = "",
    center_sub: str = "",
    good: str = "#22C55E",
    bad: str = "#EF4444",
) -> go.Figure:
    rotation = 90 if start_anchor == "top" else 270
    pos_max = max(1e-9, float(pos_max or 0))
    neg_max = max(1e-9, float(neg_max or 0))
    is_pos = (value or 0) >= 0
    frac = min(abs(value or 0) / (pos_max if is_pos else neg_max), 1.0)
    direction = "clockwise" if is_pos else "counterclockwise"
    color = good if is_pos else bad

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            values=[1],
            hole=0.74,
            sort=False,
            direction="clockwise",
            rotation=rotation,
            marker=dict(colors=['rgba(255,255,255,0.08)']),
            textinfo='none',
            showlegend=False,
            hoverinfo='skip',
        )
    )
    fig.add_trace(
        go.Pie(
            values=[frac, 1 - frac],
            hole=0.74,
            sort=False,
            direction=direction,
            rotation=rotation,
            marker=dict(colors=[color, 'rgba(255,255,255,0.06)']),
            textinfo='none',
            showlegend=False,
            hoverinfo='skip',
        )
    )
    txt = f"<b>{center_title}</b><br><span style='font-size:12px;color:#9CA3AF'>{center_sub}</span>"
    fig.update_layout(
        title=dict(text=title, y=0.95, x=0.5, xanchor="center", font=dict(size=14, color="#E5E7EB")),
        margin=dict(t=36, b=0, l=0, r=0),
        height=210,
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(x=0.5, y=0.5, text=txt, showarrow=False, font=dict(size=16, color="#E5E7EB"))],
    )
    return fig


def oneway_donut(
    title: str,
    frac: float,
    start_anchor: str = "bottom",
    center_title: str = "",
    center_sub: str = "",
) -> go.Figure:
    rotation = 270 if start_anchor == "bottom" else 90
    f = float(np.clip(frac, 0.0, 1.0))
    color = _band_color(f)
    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            values=[1],
            hole=0.74,
            sort=False,
            direction="clockwise",
            rotation=rotation,
            marker=dict(colors=['rgba(255,255,255,0.08)']),
            textinfo='none',
            showlegend=False,
            hoverinfo='skip',
        )
    )
    fig.add_trace(
        go.Pie(
            values=[f, 1 - f],
            hole=0.74,
            sort=False,
            direction="clockwise",
            rotation=rotation,
            marker=dict(colors=[color, 'rgba(255,255,255,0.06)']),
            textinfo='none',
            showlegend=False,
            hoverinfo='skip',
        )
    )
    txt = f"<b>{center_title}</b><br><span style='font-size:12px;color:#9CA3AF'>{center_sub}</span>"
    fig.update_layout(
        title=dict(text=title, y=0.95, x=0.5, xanchor="center", font=dict(size=14, color="#E5E7EB")),
        margin=dict(t=36, b=0, l=0, r=0),
        height=210,
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(x=0.5, y=0.5, text=txt, showarrow=False, font=dict(size=16, color="#E5E7EB"))],
    )
    return fig


def behavioral_score_from_mirror(mirror: dict) -> float:
    if not isinstance(mirror, dict):
        return 0.0
    vals = []
    for k in ("discipline", "patience_ratio", "efficiency", "conviction_hi_win"):
        v = mirror.get(k)
        if v is None:
            continue
        if 0 <= v <= 1:
            v = v * 100
        try:
            vals.append(float(v))
        except Exception:
            continue
    return float(np.mean(vals)) if vals else 0.0

