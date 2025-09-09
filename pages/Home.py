import streamlit as st

from .utils import render_diagram


def render(mock_data):
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
