"""Simple Streamlit dashboard for UAT/info environment.

This lightweight app mirrors the style of the existing
"03_ 📰 MACRO & NEWS" dashboard but with only a handful of
pages and mocked data.  It is intended for the Streamlit UAT
container which is exposed on port 8503 (see `WIKI_DASHBOARD_PORT`).
"""

from __future__ import annotations

import graphviz
import importlib
import plotly.graph_objects as go
import streamlit as st

from datetime import datetime


# ---------------------------------------------------------------------------
# Mock data synthesised from repo docs
# ---------------------------------------------------------------------------
mock_data = {
    "system_status": {"heartbeat": "Active", "lag_ms": 150},
    "behavioral_metrics": {
        "discipline": 87,
        "patience": 142,
        "conviction": 73,
        "efficiency": 68,
    },
    "confluence_score": 78,
    "strategies": [
        {
            "name": "SMC Liquidity Sweep",
            "setup": "Identify order blocks and fair value gaps",
            "signals": "BOS/CHOCH confirmation with volume imbalance",
            "confluence": "70-100: High; 50-69: Medium",
            "bias": "Entry on sweep; Exit at opposing block",
            "risk_gates": "Discipline >70, Patience >120s",
            "journal_hook": "Record BOS level and imbalance direction",
        },
        {
            "name": "Wyckoff Accumulation",
            "setup": "Phase detection in ranging markets",
            "signals": "Spring/Test/SOS with effort-result mismatch",
            "confluence": "80-100: Strong; <50: Avoid",
            "bias": "Long on spring confirmation",
            "risk_gates": "Conviction >75, No recent losses",
            "journal_hook": "Note phase transition and volume clues",
        },
    ],
    "whisperer_prompts": {
        "home": ["What's the system status?", "Explain Pulse architecture"],
        "strategies": ["Is this SMC setup valid?"],
        "edges": ["Am I overtrading?"],
        "risk": ["Check my risk budget"],
    },
    "journal_entries": [
        {
            "ts": "2025-09-09T10:15:00Z",
            "kind": "ENTRY",
            "text": "XAUUSD long on SMC sweep",
            "meta": {"confluence": 82},
        },
        {
            "ts": "2025-09-09T11:30:00Z",
            "kind": "PARTIAL_CLOSE",
            "text": "50% profit take",
            "meta": {"pnl": 450},
        },
    ],
}


# ---------------------------------------------------------------------------
# Helper components
# ---------------------------------------------------------------------------


def donut_chart(title: str, score: float, threshold: float = 70, subtitle: str | None = None) -> go.Figure:
    """Render a small donut with a threshold tick."""

    score = max(0.0, min(100.0, float(score)))
    frac = score / 100.0
    color = "#22C55E" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            values=[frac * 360, 360 - frac * 360],
            hole=0.75,
            sort=False,
            direction="clockwise",
            rotation=270,
            marker=dict(colors=[color, "rgba(148,163,184,0.28)"]),
            textinfo="none",
            showlegend=False,
        )
    )
    fig.add_annotation(
        text=f"<b>{title}</b><br>{score:.0f}%",
        x=0.5,
        y=0.55,
        showarrow=False,
        font=dict(size=14, color="#E5E7EB"),
    )
    if subtitle:
        fig.add_annotation(
            text=f"<span style='font-size:11px;color:#9CA3AF'>{subtitle}</span>",
            x=0.5,
            y=0.40,
            showarrow=False,
        )

    # Threshold tick
    import math

    th_deg = max(0.0, min(360.0, threshold / 100.0 * 360.0))

    def ang2xy(a: float, r: float) -> tuple[float, float]:
        th = math.radians(90 - a)
        return 0.5 + r * math.cos(th), 0.5 + r * math.sin(th)

    x0, y0 = ang2xy(th_deg, 0.48)
    x1, y1 = ang2xy(th_deg, 0.50)
    fig.add_shape(
        type="line",
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        xref="paper",
        yref="paper",
        line=dict(color="#9CA3AF", width=2),
    )

    fig.update_layout(
        margin=dict(t=6, b=6, l=6, r=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=150,
        width=150,
    )
    return fig


def render_diagram() -> graphviz.Digraph:
    """Simple architecture diagram."""

    dot = graphviz.Digraph(format="svg")
    dot.node("User")
    dot.node("Whisperer", "LLM (Whisperer)")
    dot.node("Frontend")
    dot.node("Backend", "Backend/Kernel")
    dot.node("Adapter", "Data Adapter")
    dot.node("Broker")
    dot.edges(
        [
            ("User", "Whisperer"),
            ("Whisperer", "Frontend"),
            ("Frontend", "Backend"),
            ("Backend", "Adapter"),
            ("Adapter", "Broker"),
        ]
    )
    dot.edge("Whisperer", "Backend", style="dashed")
    return dot


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .stApp { background-color: #111827; color: white; }
    h1, h2, h3 { color: white; font-family: 'Arial', sans-serif; }
    .stExpander { background-color: #1F2937; border-radius: 0.5rem; margin-bottom: 1rem; }
    .stButton > button { background-color: #2563EB; color: white; border-radius: 0.25rem; }
    .ask-whisperer { background-color: #1F2937; padding: 1rem; border-radius: 0.5rem; }
    .status-tile { background-color: #1F2937; padding: 0.5rem; border-radius: 0.25rem; text-align: center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGE_MODULES = {
    "Home": ("wiki_pages.home", "home"),
    "Strategies": ("wiki_pages.strategies", "strategies"),
    "Edges": ("wiki_pages.edges", "edges"),
    "Risk, Ops & Runbook": ("wiki_pages.risk_ops_runbook", "risk"),
}

page = st.sidebar.selectbox("Pages", list(PAGE_MODULES.keys()))

st.sidebar.markdown("<div class='ask-whisperer'>", unsafe_allow_html=True)
st.sidebar.subheader("Ask Whisperer")
module_path, prompt_key = PAGE_MODULES[page]
for prompt in mock_data["whisperer_prompts"].get(prompt_key, []):
    st.sidebar.write(f"- {prompt}")
whisper_input = st.sidebar.text_input("Your question:")
if whisper_input:
    st.sidebar.write("Whisperer: Processing... (structured response: Signal • Risk • Action • Journal note)")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

module = importlib.import_module(module_path)
module.render(mock_data)

