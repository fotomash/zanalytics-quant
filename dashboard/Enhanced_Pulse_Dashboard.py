"""Enhanced Pulse dashboard that consumes live updates via WebSocket."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from .utils.ws import subscribe

st.set_page_config(layout="wide", page_title="Zan.Pulse", page_icon="⚡")


def load_css() -> None:
    """Apply custom styles for the dashboard.

    Edit ``assets/styles.css`` to update the look and feel.
    """

    st.markdown(Path("assets/styles.css").read_text(), unsafe_allow_html=True)


load_css()


def metric_card(title, value, unit, color, trend, description):
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <h3 class="metric-title">{title}</h3>
            <div style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 0.25rem; background-color: {'#166534' if trend == 'up' else '#991B1B' if trend == 'down' else '#374151'}; color: {'#A7F3D0' if trend == 'up' else '#FCA5A5' if trend == 'down' else '#D1D5DB'};">
                {'↗' if trend == 'up' else '↘' if trend == 'down' else '→'}
            </div>
        </div>
        <div style="display: flex; align-items: baseline; gap: 0.5rem;">
            <span class="metric-value" style="color: {color};">{value}</span>
            <span class="metric-unit">{unit}</span>
        </div>
        <p class="metric-description">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def home_page():
    st.markdown("<h1 class='page-header'>Pulse Command Center</h1>", unsafe_allow_html=True)
    st.markdown("<p class='page-subheader'>Your trading cockpit - where clarity meets conviction</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Live Market Pulse
    placeholder = st.empty()
    with placeholder.container():
        cols = st.columns(4)
        with cols[0]:
            metric_card("Discipline Score", f"{st.session_state.discipline_score:.0f}", "%", "#34D399", "up", "Your adherence to predefined rules today")
        with cols[1]:
            metric_card("Patience Index", f"{st.session_state.patience_index:.0f}", "sec", "#60A5FA", "stable", "Average time between trades")
        with cols[2]:
            metric_card("Conviction Rate", f"{st.session_state.conviction_rate:.0f}", "%", "#A78BFA", "up", "Win rate of high-confidence setups")
        with cols[3]:
            metric_card("Profit Efficiency", f"{st.session_state.profit_efficiency:.0f}", "%", "#FBBF24", "down", "Profit captured vs. peak potential")
    st.subheader("Open Positions")
    positions = st.session_state.get("positions", [])
    if positions:
        positions_df = pd.DataFrame(positions)
        display_cols = [
            c
            for c in ["ticket", "symbol", "type", "volume", "price_open", "sl", "tp", "profit"]
            if c in positions_df.columns
        ]
        st.dataframe(positions_df[display_cols], use_container_width=True)
    else:
        st.caption("No open positions.")

    # Other components... (as before)
    # For brevity, the rest of the home page components are added in the main function flow below


def intelligence_page():
    st.markdown("<h1 class='page-header'>Market Intelligence Hub</h1>", unsafe_allow_html=True)
    st.markdown("<p class='page-subheader'>See what others miss - market structure decoded</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.info("This page is a representation of the Market Intelligence Hub.")


def risk_page():
    st.markdown("<h1 class='page-header'>Risk & Performance Guardian</h1>", unsafe_allow_html=True)
    st.markdown("<p class='page-subheader'>Trade with discipline, sleep with confidence</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.info("This page is a representation of the Risk & Performance Guardian.")


def whisperer_page():
    st.markdown("<h1 class='page-header'>The Whisperer Interface</h1>", unsafe_allow_html=True)
    st.markdown("<p class='page-subheader'>Your AI trading companion - always listening, always learning</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.info("This page is a representation of The Whisperer Interface.")


def journal_page():
    st.markdown("<h1 class='page-header'>Decision Journal & Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p class='page-subheader'>Learn from every decision - your path to consistent profitability</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.info("This page is a representation of the Decision Journal & Analytics.")


def _start_stream() -> None:
    if "ws_started" in st.session_state:
        return

    def _update(data: Dict[str, Any]) -> None:
        st.session_state.update(data)
        st.experimental_rerun()

    subscribe("pulse", _update)
    st.session_state.ws_started = True


def main() -> None:
    st.sidebar.title("Zan.Pulse ⚡")
    # P&L in sidebar
    pnl_placeholder = st.sidebar.empty()

    pages = {
        "Home": "Pulse Command Center",
        "Intelligence": "Market Intelligence Hub",
        "Risk": "Risk & Performance Guardian",
        "Whisperer": "The Whisperer Interface",
        "Journal": "Decision Journal & Analytics",
    }

    selection_key = st.sidebar.radio("Navigation", list(pages.keys()), format_func=lambda page: pages[page])

    # Initialize state
    if "discipline_score" not in st.session_state:
        st.session_state.discipline_score = 87
        st.session_state.patience_index = 142
        st.session_state.conviction_rate = 73
        st.session_state.profit_efficiency = 68
        st.session_state.current_pnl = 2847
        st.session_state.daily_target = 4000

    _start_stream()

    pnl_color = "green" if st.session_state.current_pnl >= 0 else "red"
    pnl_placeholder.markdown(
        f"### P&L: <span style='color:{pnl_color};'>${st.session_state.current_pnl:,.0f}</span>",
        unsafe_allow_html=True,
    )

    # Page rendering
    if selection_key == "Home":
        home_page()
    elif selection_key == "Intelligence":
        intelligence_page()
    elif selection_key == "Risk":
        risk_page()
    elif selection_key == "Whisperer":
        whisperer_page()
    elif selection_key == "Journal":
        journal_page()


if __name__ == "__main__":
    main()
