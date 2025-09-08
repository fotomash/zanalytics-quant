import math
from typing import Dict, Optional
import plotly.graph_objects as go


def _band(score: float) -> str:
    try:
        s = float(score)
    except Exception:
        s = 0.0
    if s >= 70:
        return 'green'
    if s >= 50:
        return 'amber'
    return 'red'


def _band_color(band: str) -> str:
    return {'green': '#22C55E', 'amber': '#FBBF24', 'red': '#EF4444'}.get(band, '#9CA3AF')


def gate_donut(*, title: str, score: float, threshold: float = 70, subtitle: Optional[str] = None) -> go.Figure:
    s = max(0.0, min(100.0, float(score or 0)))
    frac = s / 100.0
    band = _band(s)
    col = _band_color(band)
    fig = go.Figure()
    fig.add_trace(go.Pie(values=[frac * 360.0, 360.0 - frac * 360.0], hole=0.75, sort=False,
                         direction='clockwise', rotation=270,
                         marker=dict(colors=[col, 'rgba(148,163,184,0.28)']), textinfo='none', showlegend=False))
    fig.add_annotation(text=f"<b>{title}</b><br>{s:.0f}%", x=0.5, y=0.55, showarrow=False,
                       font=dict(size=14, color='#E5E7EB'))
    if subtitle:
        fig.add_annotation(text=f"<span style='font-size:11px;color:#9CA3AF'>{subtitle}</span>", x=0.5, y=0.40, showarrow=False)
    # threshold tick
    th_deg = max(0.0, min(360.0, (float(threshold) / 100.0) * 360.0))
    def ang2xy(a: float, r: float):
        th = math.radians(90 - a)
        return 0.5 + r * math.cos(th), 0.5 + r * math.sin(th)
    x0, y0 = ang2xy(th_deg, 0.48)
    x1, y1 = ang2xy(th_deg, 0.50)
    fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1, xref='paper', yref='paper',
                  line=dict(color='#9CA3AF', width=2))
    fig.update_layout(margin=dict(t=6, b=6, l=6, r=6), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


def confluence_score(gates: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    if not gates:
        return 0.0
    if not weights:
        weights = {k: 1.0 for k in gates}
    tot = sum(weights.values()) or 1.0
    return sum(max(0.0, min(100.0, float(gates.get(k, 0)))) * float(weights.get(k, 0.0)) for k in gates) / tot


def confluence_donut(*, title: str, gates: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> go.Figure:
    score = confluence_score(gates, weights)
    return gate_donut(title=title, score=score, threshold=70, subtitle="Composite")

