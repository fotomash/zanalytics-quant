import streamlit as st
from wiki_dashboard import donut_chart


def render(mock_data):
    """Render the Strategies page."""
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
            st.plotly_chart(
                donut_chart("Example Score", mock_data["confluence_score"]), use_container_width=True
            )
            st.write(f"**Bias**: {strat['bias']}")
            st.write(f"**Risk Gates**: {strat['risk_gates']}")
            st.write(f"**Journal Hook**: {strat['journal_hook']}")
    with st.expander("What to ask Whisperer"):
        st.write("- Pre-trade: Validate this setup?")
        st.write("- Post-trade: Journal with note on bias.")
