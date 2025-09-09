"""Simple Streamlit dashboard for UAT/info environment.

This lightweight app mirrors the style of the existing
"03_ 📰 MACRO & NEWS" dashboard but with only a handful of
pages and mocked data.  It is intended for the Streamlit UAT
container which is exposed on port 8503 (see `WIKI_DASHBOARD_PORT`).
"""

from __future__ import annotations

import streamlit as st

from datetime import datetime

from pages import Edges, Home, RiskOpsRunbook, Strategies, HowTo


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
        "howto": ["How do I use the Confluence Scorer?", "Best way to ask Whisperer questions?"],
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

PAGE_KEYS = {
    "Home": "home",
    "Strategies": "strategies",
    "Edges": "edges",
    "Risk, Ops & Runbook": "risk",
    "HowTo": "howto",
}

page_modules = {
    "Home": Home,
    "Strategies": Strategies,
    "Edges": Edges,
    "Risk, Ops & Runbook": RiskOpsRunbook,
    "HowTo": HowTo,
}

missing_keys = set(page_modules) - set(PAGE_KEYS)
if missing_keys:
    raise KeyError(f"Missing PAGE_KEYS for: {', '.join(missing_keys)}")

page = st.sidebar.selectbox("Pages", list(page_modules.keys()))

# Link to documentation
st.sidebar.markdown(
    "[How to use the Confluence Scorer](docs/HowTo_Confluence_Scorer.md)"
)

st.sidebar.markdown("<div class='ask-whisperer'>", unsafe_allow_html=True)
st.sidebar.subheader("Ask Whisperer")
for prompt in mock_data["whisperer_prompts"].get(PAGE_KEYS.get(page, ""), []):
    st.sidebar.write(f"- {prompt}")
whisper_input = st.sidebar.text_input("Your question:")
if whisper_input:
    st.sidebar.write("Whisperer: Processing... (structured response: Signal • Risk • Action • Journal note)")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

page_modules[page].render(mock_data)

