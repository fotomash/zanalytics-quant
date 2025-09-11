import time
import requests
import plotly.graph_objects as go
import streamlit as st
from dashboard.utils.streamlit_api import api_url


def render_discipline_posture_panel():
    try:
        data = requests.get(api_url("api/v1/discipline/summary"), timeout=2).json()
    except Exception:
        st.info("Discipline summary unavailable.")
        return
    today = data.get('today')
    yesterday = data.get('yesterday')
    seven = data.get('seven_day') or []
    events = data.get('events_today') or []

    # Seven day bars
    labels = [it.get('date') for it in seven]
    values = [float(it.get('score') or 0) for it in seven]
    if not labels or not values:
        labels = [time.strftime('%Y-%m-%d')]
        values = [today or 0]

    # Color per bar by score: green >=70, amber 50-69, red <50
    colors = [
        ("#22C55E" if v >= 70 else ("#FBBF24" if v >= 50 else "#EF4444"))
        for v in values
    ]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    fig.add_hline(y=70, line_dash="dot", line_color="#FBBF24")
    fig.add_hline(y=50, line_dash="dot", line_color="#EF4444")
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor='#0B1220', plot_bgcolor='#0B1220',
                      showlegend=False, xaxis=dict(title=None), yaxis=dict(range=[0,100], title=None))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    cols = st.columns(3)
    cols[0].markdown(f"**Today:** <span style='color:#22C55E'>{int(today or 0)}</span>", unsafe_allow_html=True)
    cols[1].markdown(f"**Yesterday:** {int(yesterday or 0) if yesterday is not None else '—'}", unsafe_allow_html=True)
    if values:
        avg7 = sum(values)/len(values)
        cols[2].markdown(f"**7‑day avg:** {int(avg7)}", unsafe_allow_html=True)

    if events:
        with st.expander("Today's discipline events"):
            for ev in events[:10]:
                kind = ev.get('kind') or 'event'
                delta = ev.get('delta') or 0
                st.write(f"• {kind} ({int(delta):+d})")
