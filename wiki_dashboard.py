"""Simple Streamlit dashboard for UAT/info environment.

This lightweight app mirrors the style of the existing
"03_ 📰 MACRO & NEWS" dashboard but with only a handful of
pages and mocked data.  It is intended for the Streamlit UAT
container which is exposed on port 8503 (see `WIKI_DASHBOARD_PORT`).
"""

from __future__ import annotations

import graphviz
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

pages = ["Home", "Strategies", "Edges", "Risk, Ops & Runbook"]
page = st.sidebar.selectbox("Pages", pages)

st.sidebar.markdown("<div class='ask-whisperer'>", unsafe_allow_html=True)
st.sidebar.subheader("Ask Whisperer")
for prompt in mock_data["whisperer_prompts"].get(page.lower(), []):
    st.sidebar.write(f"- {prompt}")
whisper_input = st.sidebar.text_input("Your question:")
if whisper_input:
    st.sidebar.write("Whisperer: Processing... (structured response: Signal • Risk • Action • Journal note)")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

if page == "Home":
    st.title("What Pulse Is (and Why It Matters)")
    st.image("https://placeholder.com/800x300?text=O3+Hero+Image", use_column_width=True)
    st.subheader("System Architecture")
    st.graphviz_chart(render_diagram())
    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            "<div class='status-tile'>What it does: Filters noise into high-conviction trades with AI nudges.</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            "<div class='status-tile'>What's live: Broker feed, Whisperer, Journaling, Behavioral gates.</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            "<div class='status-tile'>What's next: Full Kafka journaling, expanded strategies.</div>",
            unsafe_allow_html=True,
        )
    st.subheader("Live Status")
    st.write(
        f"Heartbeat: {mock_data['system_status']['heartbeat']} | Lag: {mock_data['system_status']['lag_ms']}ms"
    )
    with st.expander("What to ask Whisperer"):
        st.write("- Is my entry justified at current confluence?")
        st.write("- Explain this score drop.")

elif page == "Strategies":
    st.title("Strategies (Consolidated Cards)")
    with st.expander("How to read a Strategy Card"):
        st.write(
            "Setup: Market conditions. Signals: Entry triggers. Confluence: Score bands. Bias: Direction. Risk gates: Guards. Journal hook: What to log."
        )
        st.write("Failure modes: Low confluence ignores; misread signals lead to traps.")
    for strat in mock_data["strategies"]:
        with st.expander(strat["name"]):
            st.write(f"**Setup**: {strat['setup']}")
            st.write(f"**Signals**: {strat['signals']}")
            st.write(f"**Confluence**: {strat['confluence']}")
            st.plotly_chart(donut_chart("Example Score", mock_data["confluence_score"]), use_container_width=True)
            st.write(f"**Bias**: {strat['bias']}")
            st.write(f"**Risk Gates**: {strat['risk_gates']}")
            st.write(f"**Journal Hook**: {strat['journal_hook']}")
    with st.expander("What to ask Whisperer"):
        st.write("- Pre-trade: Validate this setup?")
        st.write("- Post-trade: Journal with note on bias.")

elif page == "Edges":
    st.title("Edges: Behavioral + Technical")
    st.subheader("Behavioral Edge")
    cols = st.columns(4)
    metrics = mock_data["behavioral_metrics"]
    with cols[0]:
        st.plotly_chart(
            donut_chart("Discipline", metrics["discipline"], subtitle="Rule adherence")
        )
    with cols[1]:
        st.plotly_chart(
            donut_chart("Patience", min(100, metrics["patience"] / 3), subtitle="Time between trades")
        )
    with cols[2]:
        st.plotly_chart(
            donut_chart("Conviction", metrics["conviction"], subtitle="Confidence wins")
        )
    with cols[3]:
        st.plotly_chart(
            donut_chart("Efficiency", metrics["efficiency"], subtitle="Profit captured")
        )
    st.write(
        "Enforced by Risk Enforcer: Cooldowns after losses, max 3-5 trades/day, anti-revenge detection."
    )
    with st.expander("What Behavioral Means"):
        st.write(
            "Discipline prevents overtrading; Patience curbs FOMO; Conviction checks intuition; Efficiency maximizes R:R."
        )
    st.subheader("Technical Edge")
    st.write("MIDAS: Data hygiene for VWAP channels. SMC/Wyckoff: Structure over TA. Microstructure: Order flow timing via NCOS.")
    fig = go.Figure(
        go.Pie(labels=["SMC", "Wyckoff", "TA", "Micro"], values=[40, 30, 15, 15], hole=0.3)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.write("Bands: Green >70 (act), Amber 50-70 (warn), Red <50 (block).")
    with st.expander("What to ask Whisperer"):
        st.write("- Am I violating cooldown?")
        st.write("- Adjust confluence weights?")

else:
    st.title("Risk, Ops & Runbook")
    st.subheader("Risk Mapping")
    st.write("Confluence >80: Allow full size. 50-80: Warn, half size. <50: Block.")
    st.write("Examples: Allowed (high conv), Warn (medium, cooldown), Blocked (low disc).")
    with st.expander("Allowed / Warn / Blocked Examples"):
        st.write("- Allowed: Green gates, position_open via Actions Bus.")
        st.write("- Warn: Amber patience, suggest hedge.")
        st.write("- Blocked: Red efficiency, reject modify.")
    st.subheader("Journal Loop")
    st.write("Records: ENTRY/CLOSE/PARTIAL/HEDGE/MODIFY with meta (from JOURNALING.md).")
    for entry in mock_data["journal_entries"]:
        st.write(
            f"{entry['ts']} - {entry['kind']}: {entry['text']} (Confluence: {entry['meta'].get('confluence', 'N/A')})"
        )
    st.write("Weekly reviews: Detect drift via behavior_events.")
    st.subheader("Operations")
    st.write(
        "Run: streamlit run wiki_dashboard.py --server.port="
        "{st.secrets.get('WIKI_DASHBOARD_PORT', 8503)}"
    )
    st.write("Route: Traefik host WIKI_DASHBOARD; verify Django health /api/pulse/health.")
    with st.expander("Incident Checklist"):
        st.write("- Capture: Journal append, screenshot.")
        st.write("- Notify: Dev team via alert.")
        st.write("- Verify: Check Kafka/Redis logs.")

