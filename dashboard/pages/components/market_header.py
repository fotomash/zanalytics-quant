import streamlit as st
import requests
from dashboard.utils.streamlit_api import api_url


def _sparkline(values, color="#93c5fd"):
    import plotly.graph_objects as go
    fig = go.Figure(go.Scatter(y=values or [], mode='lines', line=dict(color=color, width=1.5), hoverinfo='skip'))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), height=40)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def render_market_header():
    """Slim header with VIX, DXY sparklines and next high-impact news.
    Tries optional internal endpoints; degrades gracefully if unavailable.
    """
    vix = {'series': [], 'value': None}
    dxy = {'series': [], 'value': None}
    news = {'label': None, 'countdown': None}
    # Optional internal endpoints
    try:
        r = requests.get(api_url("api/v1/market/mini"), timeout=1.2)
        if r.ok:
            data = r.json() or {}
            vix = data.get('vix') or vix
            dxy = data.get('dxy') or dxy
            news = data.get('news') or news
            regime = data.get('regime')
    except Exception:
        pass

    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        st.caption("VIX")
        _sparkline(vix.get('series') or [], color="#60a5fa")
    with c2:
        st.caption("DXY")
        _sparkline(dxy.get('series') or [], color="#a78bfa")
    with c3:
        label = news.get('label') or "—"
        cd = news.get('countdown') or ""
        st.caption(f"🗞️ {label} {cd}")
        if 'regime' in locals() and regime:
            st.caption(f"📈 Regime: {regime}")
