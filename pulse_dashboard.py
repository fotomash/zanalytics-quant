
import streamlit as st
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Zan.Pulse", page_icon="⚡")

def inject_custom_css():
    st.markdown("""
    <style>
        /* General Styles */
        .stApp {
            background-color: #111827; /* bg-gray-900 */
            color: #D1D5DB; /* text-gray-300 */
        }
        /* Sidebar */
        .st-emotion-cache-16txtl3 {
            background-color: #1F2937;
            border-right: 1px solid #374151;
        }
        
        /* Metric Card */
        .metric-card {
            background-color: #1F2937; /* bg-gray-800 */
            border: 1px solid #374151; /* border-gray-700 */
            border-radius: 0.5rem; /* rounded-lg */
            padding: 1.5rem; /* p-6 */
            transition: all 0.3s;
            height: 100%;
        }
        .metric-card:hover {
            border-color: #4B5563; /* hover:border-gray-600 */
        }
        .metric-title {
            font-size: 0.875rem; /* text-sm */
            font-weight: 500; /* font-medium */
            color: #D1D5DB; /* text-gray-300 */
        }
        .metric-value {
            font-size: 1.875rem; /* text-3xl */
            font-weight: 700; /* font-bold */
        }
        .metric-unit {
            font-size: 0.875rem; /* text-sm */
            color: #9CA3AF; /* text-gray-400 */
        }
        .metric-description {
            font-size: 0.75rem; /* text-xs */
            color: #9CA3AF; /* text-gray-400 */
            margin-top: 0.5rem;
        }
        
        /* Page Headers */
        .page-header {
            text-align: center;
            color: white;
            font-size: 2.25rem; /* text-4xl */
            font-weight: 700; /* font-bold */
        }
        .page-subheader {
            text-align: center;
            color: #9CA3AF; /* text-gray-400 */
            font-size: 1.125rem; /* text-lg */
        }

    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

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

def main():
    st.sidebar.title("Zan.Pulse ⚡")
    
    # P&L in sidebar
    pnl_placeholder = st.sidebar.empty()
    
    pages = {
        "Home": "Pulse Command Center",
        "Intelligence": "Market Intelligence Hub",
        "Risk": "Risk & Performance Guardian",
        "Whisperer": "The Whisperer Interface",
        "Journal": "Decision Journal & Analytics"
    }
    
    selection_key = st.sidebar.radio("Navigation", list(pages.keys()), format_func=lambda page: pages[page])

    # Initialize state
    if 'discipline_score' not in st.session_state:
        st.session_state.discipline_score = 87
        st.session_state.patience_index = 142
        st.session_state.conviction_rate = 73
        st.session_state.profit_efficiency = 68
        st.session_state.current_pnl = 2847
        st.session_state.daily_target = 4000

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

    # Simulate real-time updates
    while True:
        st.session_state.current_pnl += (np.random.random() - 0.5) * 50
        st.session_state.discipline_score = max(60, min(100, st.session_state.discipline_score + (np.random.random() - 0.5) * 2))
        st.session_state.patience_index = max(30, min(300, st.session_state.patience_index + (np.random.random() - 0.5) * 10))

        pnl_color = "green" if st.session_state.current_pnl >= 0 else "red"
        pnl_placeholder.markdown(f"### P&L: <span style='color:{pnl_color};'>${st.session_state.current_pnl:,.0f}</span>", unsafe_allow_html=True)
        
        if selection_key == "Home":
            st.rerun()
        
        time.sleep(3)


if __name__ == "__main__":
    main()
