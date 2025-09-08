import streamlit as st
import plotly.graph_objects as go
import requests
from dashboard.utils.streamlit_api import api_url


def render_profit_horizon(limit: int = 20):
    try:
        data = requests.get(api_url(f"api/v1/profit-horizon?limit={limit}"), timeout=2).json()
    except Exception:
        st.info("Profit Horizon unavailable.")
        return
    if not isinstance(data, list) or not data:
        st.info("No closed trades yet.")
        return
    ids = []
    final_vals = []
    peak_vals = []
    durs = []
    use_usd = False
    for it in data:
        ids.append(it.get('id'))
        pr = it.get('pnl_r')
        pk = it.get('peak_r')
        if pr is None and pk is None:
            pr = it.get('pnl_usd'); pk = it.get('peak_usd'); use_usd = True
        final_vals.append(pr or 0)
        peak_vals.append(max(pr or 0, pk or 0))
        durs.append(it.get('dur_min'))

    fig = go.Figure()
    # Final P&L bars
    fig.add_trace(go.Bar(x=ids, y=final_vals,
                         marker_color=["#22c55e" if (v or 0) >= 0 else "#ef4444" for v in final_vals],
                         name="Final"))
    # Ghost to peak
    ghost = [(peak_vals[i] - final_vals[i]) if (peak_vals[i] or 0) >= (final_vals[i] or 0) else 0 for i in range(len(ids))]
    fig.add_trace(go.Bar(x=ids, y=ghost, base=final_vals,
                         marker_color="rgba(34,211,238,0.35)", name="Peak (ghost)",
                         hoverinfo="skip"))

    fig.update_layout(
        barmode='stack',
        showlegend=True,
        height=320,
        margin=dict(l=10, r=10, t=10, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Trade', tickmode='linear'),
        yaxis=dict(title=('P&L (USD)' if use_usd else 'R multiple')),
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
