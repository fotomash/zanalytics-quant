# Donut Confluence Score Design

This document standardizes the donut components for behavioral gates and the composite confluence score.

## Single Gate Donut

- Inputs: `title`, `score` (0..100), `threshold` (0..100), optional `subtitle`.
- Bands: `score>=70→green`, `50–69→amber`, `<50→red`.
- Threshold tick: thin radial mark at `threshold/100 * 360°`.

Concept snippet (using Plotly):

```python
import plotly.graph_objects as go

def gate_donut(title: str, score: float, threshold: float, subtitle: str | None = None) -> go.Figure:
    s = max(0.0, min(100.0, float(score)))
    frac = s / 100.0
    col = '#22C55E' if s >= 70 else ('#FBBF24' if s >= 50 else '#EF4444')
    fig = go.Figure()
    fig.add_trace(go.Pie(values=[frac*360, 360-frac*360], hole=0.75, sort=False,
                         direction='clockwise', rotation=270,
                         marker=dict(colors=[col, 'rgba(148,163,184,0.28)']), textinfo='none', showlegend=False))
    # center text
    fig.add_annotation(text=f"<b>{title}</b><br>{s:.0f}%", x=0.5, y=0.55, showarrow=False,
                       font=dict(size=14, color='#E5E7EB'))
    if subtitle:
        fig.add_annotation(text=f"<span style='font-size:11px;color:#9CA3AF'>{subtitle}</span>", x=0.5, y=0.40, showarrow=False)
    # threshold tick
    th_deg = max(0.0, min(360.0, threshold/100.0 * 360.0))
    # simple radial tick near outer ring
    import math
    def ang2xy(a, r):
        th = math.radians(90 - a)
        return 0.5 + r*math.cos(th), 0.5 + r*math.sin(th)
    x0,y0 = ang2xy(th_deg, 0.48)
    x1,y1 = ang2xy(th_deg, 0.50)
    fig.add_shape(type='line', x0=x0, y0=y0, x1=x1, y1=y1, xref='paper', yref='paper',
                  line=dict(color='#9CA3AF', width=2))
    fig.update_layout(margin=dict(t=6,b=6,l=6,r=6), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig
```

## Confluence Donut (Composite)

- Inputs: dict of gate scores, optional weights; outputs composite score.
- Center text: title and composite (e.g., “🧭 Behavioral Confluence” / “58%”).
- Optional lock icon if any hard fails (<40).

Composite calculation example:

```python
def confluence_score(gates: dict[str, float], weights: dict[str, float] | None = None) -> float:
    if not gates:
        return 0.0
    if not weights:
        weights = {k: 1.0 for k in gates}
    tot = sum(weights.values()) or 1.0
    return sum(max(0.0, min(100.0, gates[k])) * weights.get(k, 0.0) for k in gates) / tot
```

Render by composing 4 mini donuts around a central composite ring, or reuse `dashboard/components/ui_concentric.py`:
- Outer: PnL or composite
- Middle: risk/exposure split
- Inner: behavioral summary

## Icons & Tooltips

- Gates failing hard (<40): add a “lock” glyph and show reason on hover.
- Tooltip text sources: mirror API or journal messages.

## Where to implement

- Extend `dashboard/components/ui_concentric.py` with `gate_donut()` and `confluence_donut()` wrappers, or add a new `dashboard/utils/plotly_gates.py` as a thin layer that calls existing primitives.

