import streamlit as st
import requests
import plotly.graph_objects as go
from dashboard.utils.streamlit_api import api_url


def _get_pulse_detail(symbol: str) -> dict:
    try:
        r = requests.get(api_url(f"api/v1/feed/pulse-detail?symbol={symbol}"), timeout=1.5)
        if r.ok:
            return r.json() or {}
    except Exception:
        return {}
    return {}


def render(symbol: str, *, height: int = 260) -> None:
    data = _get_pulse_detail(symbol)
    gates = {
        "Context": (data.get("structure") or {}).get("passed"),  # structure often implies context
        "Liquidity": (data.get("liquidity") or {}).get("passed"),
        "Structure": (data.get("structure") or {}).get("passed"),
        "Imbalance": (data.get("imbalance") or {}).get("passed"),
        "Risk": (data.get("risk") or {}).get("passed"),
        "Wyckoff": (data.get("wyckoff") or {}).get("passed"),
    }
    conf = (data.get("confluence") or {}).get("confidence")

    labels = list(gates.keys())
    values = []
    for k in labels:
        v = gates.get(k)
        values.append(100.0 if bool(v) else 0.0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=values,
                         marker_color=[
                             "#22C55E" if v >= 60 else ("#FBBF24" if v >= 30 else "#EF4444") for v in values
                         ],
                         text=[f"{int(v)}%" for v in values], textposition="outside"))
    try:
        pct = float(conf or 0.0) * 100.0
        ttl = f"Confluence {pct:.0f}%"
    except Exception:
        ttl = "Confluence —"
    fig.update_layout(
        title=dict(text=ttl, x=0.5, xanchor="center"),
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

