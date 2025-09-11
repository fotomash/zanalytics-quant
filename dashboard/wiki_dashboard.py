
"""Simple Streamlit dashboard for UAT/info environment.

This lightweight app mirrors the style of the existing
"03_ 📰 MACRO & NEWS" dashboard but with only a handful of
pages and mocked data.  It is intended for the Streamlit UAT
container which is exposed on port 8503 (see `WIKI_DASHBOARD_PORT`).
"""



import graphviz
import importlib
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pages
from pages import Edges, Home, RiskOpsRunbook, Strategies, HowTo, InteractiveDemo



# ---------------------------------------------------------------------------
# Mock data synthesised from repo docs
# ---------------------------------------------------------------------------

# Mock data synthesised from repo docs, attachments, and previous dashboards
# Updated for current date: September 10, 2025

mock_data = {
    "system_status": {"heartbeat": "Active", "lag_ms": 150},
    "behavioral_metrics": {"discipline": 87, "patience": 142, "conviction": 73, "efficiency": 68},
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
        "howto": ["How do I use the Confluence Scorer?", "Best way to ask Whisperer questions?"],
        "interactive": ["Can you walk me through a demo?"],
    },
    "journal_entries": [

        {
            "name": "Wyckoff Distribution",
            "setup": "Upthrusts in topping patterns",
            "signals": "UTAD/Test/SOW with declining volume",
            "confluence": "75-100: Bearish; Monitor for breakdown",
            "bias": "Short on UTAD failure",
            "risk_gates": "Efficiency >65, Cooldown active",
            "journal_hook": "Log SOW levels and bearish divergence",
        },
        {
            "name": "MIDAS VWAP Channels",
            "setup": "Dynamic support/resistance from volume-weighted anchors",
            "signals": "Bounce from lower channel or break of upper",
            "confluence": "60-90: Valid; Combine with SMC",
            "bias": "Mean reversion trades",
            "risk_gates": "Patience index high, Risk budget <50%",
            "journal_hook": "Anchor point and deviation %",
        },
        {
            "name": "NCOS Timing",
            "setup": "News Catalyst Orderflow Sync",
            "signals": "Pre-news buildup with institutional footprints",
            "confluence": "85-100: High impact; <70: Skip",
            "bias": "Fade extremes post-news",
            "risk_gates": "All gates green, Max trades not exceeded",
            "journal_hook": "Event importance and orderflow shift",
        },
        {
            "name": "TA Confluence",
            "setup": "Multi-indicator alignment (RSI, MACD, Fibs)",
            "signals": "Divergence + Fib retrace",
            "confluence": "50-80: Supportive; Not standalone",
            "bias": "Trend continuation",
            "risk_gates": "Conviction calibrated to history",
            "journal_hook": "Indicator values and cross-verification",
        },
    ],
    "whisperer_prompts": {
        "info": ["How to use Confluence Scorer?", "Example Whisperer uses"],
        "interaction": ["Interact with LLM for feedback", "What's the flow for a trade?"],
    },
    "journal_entries": [
        {"ts": "2025-09-10T10:15:00Z", "kind": "ENTRY", "text": "XAUUSD long on SMC sweep", "meta": {"confluence": 82}},
        {"ts": "2025-09-10T11:30:00Z", "kind": "PARTIAL_CLOSE", "text": "50% profit take", "meta": {"pnl": 450}},
    ],
}


# Donut Chart Helper
def donut_chart(title, score, threshold=70, subtitle=None):
    score = max(0, min(100, float(score)))
    frac = score / 100
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
    import math

    th_deg = max(0, min(360, threshold / 100 * 360))

    def ang2xy(a, r):
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


# Diagram Helper

def render_diagram():
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


# Custom CSS
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

PAGE_MODULES = {
    "Home": ("wiki_pages.home", "home"),
    "Strategies": ("wiki_pages.strategies", "strategies"),
    "Edges": ("wiki_pages.edges", "edges"),
    "Risk, Ops & Runbook": ("wiki_pages.risk_ops_runbook", "risk"),
}

page = st.sidebar.selectbox("Pages", list(PAGE_MODULES.keys()))

PAGE_KEYS = {
    "Home": "home",
    "Strategies": "strategies",
    "Edges": "edges",
    "Risk, Ops & Runbook": "risk",
    "HowTo": "howto",
    "Interactive Demo": "interactive",
}

page_modules = {

    "Home": pages.Home,
    "Strategies": pages.Strategies,
    "Edges": pages.Edges,
    "Risk, Ops & Runbook": pages.RiskOpsRunbook,
    "HowTo": pages.HowTo,
}
selected_name = st.sidebar.selectbox("Pages", list(page_modules.keys()))
selected_page = page_modules[selected_name]

    "Home": Home,
    "Strategies": Strategies,
    "Edges": Edges,
    "Risk, Ops & Runbook": RiskOpsRunbook,
    "HowTo": HowTo,
    "Interactive Demo": InteractiveDemo,
}


# Navigation (sidebar for dashboards)
dashboards = ["Info (Landing)", "Interaction"]
dashboard = st.sidebar.selectbox("Dashboards", dashboards)

# Persistent Whisperer Panel (context-aware)
# To eliminate repeated permission prompts for LLM API calls to mcp1.zanalytics.app,
# ensure openapi.actions.yaml defines a trusted connector with always_allow.
st.sidebar.markdown("<div class='ask-whisperer'>", unsafe_allow_html=True)
st.sidebar.subheader("Ask Whisperer")

for prompt in mock_data["whisperer_prompts"].get(selected_name.lower(), []):
=======

module_path, prompt_key = PAGE_MODULES[page]
for prompt in mock_data["whisperer_prompts"].get(prompt_key, []):

for prompt in mock_data["whisperer_prompts"].get(dashboard.lower().split()[0], []):

    st.sidebar.write(f"- {prompt}")
whisper_input = st.sidebar.text_input("Your question:")
if whisper_input:
    st.sidebar.write(
        "Whisperer: Processing... (structured response: Signal • Risk • Action • Journal note)"
    )
st.sidebar.markdown("</div>", unsafe_allow_html=True)

selected_page.render(mock_data)

module = importlib.import_module(module_path)
module.render(mock_data)

# Dashboard Content
if dashboard == "Info (Landing)":
    st.title("Zan.Pulse Info")
    st.image("https://placeholder.com/800x300?text=O3+Hero+Image", use_column_width=True)
    st.subheader("How to Use Confluence Scorer")
    st.write("The scorer aggregates SMC, Wyckoff, TA signals into a 0-100 score. Use it pre-entry to filter setups.")
    st.plotly_chart(donut_chart("Confluence", mock_data["confluence_score"]))
    with st.expander("Example Uses"):
        st.write("- Score >80: High-conviction entry. Example: BOS with FVG confluence at 85%.")
        st.write("- Score 50-80: Monitor for improvement. Example: Partial Wyckoff alignment at 65%—wait for volume confirmation.")
        st.write("- Score <50: Skip. Example: Conflicting HTF bias drops score to 40%.")
    st.subheader("How to Use Whisperer")
    st.write("Voice/text interface for real-time guidance. Knows your risk, positions, and market state.")
    with st.expander("Example Uses"):
        st.write("- 'Validate this XAUUSD setup': Returns confluence score, gates check, and suggestion.")
        st.write("- 'Am I overtrading?': Analyzes patience index and trades today, suggests cooldown if needed.")
        st.write("- 'Journal last trade': Appends structured entry with meta (e.g., confluence, reason).")
    st.subheader("Design Overview")
    st.graphviz_chart(render_diagram())
    st.write("Modular: Context → Structure → POI → Entry → Risk → Management. Scalable AI-native for trading and beyond.")


elif dashboard == "Interaction":
    st.title("Interact with Dashboard")
    st.write("Flow: Query Whisperer → Get feedback → Act via API → Journal outcome. All via natural language.")
    st.subheader("Interaction Flow")
    st.write("1. Ask LLM (Whisperer) for setup validation via sidebar.")
    st.write("2. View behavioral donuts for gates check.")
    cols = st.columns(4)
    metrics = mock_data["behavioral_metrics"]
    with cols[0]:
        st.plotly_chart(donut_chart("Discipline", metrics["discipline"], subtitle="Rule adherence"))
    with cols[1]:
        st.plotly_chart(
            donut_chart("Patience", min(100, metrics["patience"] / 3), subtitle="Time between trades")
        )
    with cols[2]:
        st.plotly_chart(donut_chart("Conviction", metrics["conviction"], subtitle="Confidence wins"))
    with cols[3]:
        st.plotly_chart(donut_chart("Efficiency", metrics["efficiency"], subtitle="Profit captured"))
    st.write("3. Execute: Whisperer can trigger position_open/close if trusted.")
    st.write("4. Feedback: Get proactive nudges on risk/behavior.")
    with st.expander("Ideas for LLM Interaction"):
        st.write("- Real-time chat: Query 'Am I overtrading?' for instant gates check and advice.")
        st.write("- Feedback loop: After trade, ask 'Analyze this outcome' for insights and journal auto-append.")
        st.write("- Flow integration: 'Scan XAUUSD setups' → Returns opportunities with scores; follow up 'Enter long?' to execute if valid.")
    st.subheader("Journal Interaction")
    for entry in mock_data["journal_entries"]:
        st.write(
            f"{entry['ts']} - {entry['kind']}: {entry['text']} (Confluence: {entry['meta']['confluence']})"
        )
    if st.button("Add Mock Journal Entry"):
        st.write("Appended: New ENTRY with confluence 85 (simulated).")
