import os
import math
import requests
import plotly.graph_objects as go


def _fetch_snapshot(base: str) -> dict:
    try:
        r = requests.get(f"{base}/api/v1/state/snapshot", timeout=1.5)
        if r.ok:
            return r.json() or {}
    except Exception:
        return {}
    return {}


def render(st):
    base = os.getenv('DJANGO_API_URL', 'http://django:8000').rstrip('/')
    snap = _fetch_snapshot(base)
    mirror = snap.get('mirror') or {}

    # Extract metrics (tolerant)
    disc = mirror.get('discipline')
    pat_ratio = mirror.get('patience_ratio')  # -0.5..+0.5 → scale to 0..100
    try:
        patience = None if pat_ratio is None else round((float(pat_ratio) + 0.5) * 100.0, 1)
    except Exception:
        patience = None
    conv_hi = mirror.get('conviction_hi_win')
    eff = mirror.get('efficiency')

    rings = [
        ("Discipline", disc, "#22C55E"),
        ("Patience", patience, "#3B82F6"),
        ("Conviction", conv_hi, "#8B5CF6"),
        ("Efficiency", eff, "#06B6D4"),
    ]
    # Build concentric donuts
    fig = go.Figure()
    sizes = [1.00, 0.82, 0.64, 0.46]
    track = 'rgba(31,41,55,0.30)'
    start_at_noon = 90
    for i, (name, val, color) in enumerate(rings):
        s = sizes[i]
        off = (1.0 - s) / 2.0
        hole = 0.80
        # Track
        fig.add_trace(go.Pie(values=[100], labels=[""], hole=hole, rotation=start_at_noon, direction='clockwise',
                              marker=dict(colors=[track]), textinfo='none', showlegend=False, sort=False,
                              domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off])))
        try:
            v = float(val)
            if math.isnan(v):
                raise ValueError
            v = max(0.0, min(100.0, v))
        except Exception:
            v = 0.0
        fig.add_trace(go.Pie(values=[v, 100 - v], labels=[name, ""], hole=hole, rotation=start_at_noon,
                              direction='clockwise', marker=dict(colors=[color, 'rgba(0,0,0,0)']),
                              textinfo='none', hovertemplate=f"{name}: {v:.0f}%<extra></extra>", showlegend=False,
                              sort=False, domain=dict(x=[off, 1.0 - off], y=[off, 1.0 - off])))

    fig.add_annotation(text=f"Behavioral\nScorecard", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=16, color="#ffffff"))
    fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    st.markdown("#### 🧭 Behavioral Gate Scorecard")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

