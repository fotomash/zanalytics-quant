import streamlit as st
import plotly.graph_objects as go
from wiki_dashboard import donut_chart


def render(mock_data):
    """Render the Edges page."""
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
