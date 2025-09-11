import streamlit as st


def render(mock_data):
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
        f"Run: streamlit run dashboards/info/main.py --server.port={st.secrets.get('WIKI_DASHBOARD_PORT', 8503)}"
    )
    st.write("Route: Traefik host WIKI_DASHBOARD; verify Django health /api/pulse/health.")
    with st.expander("Incident Checklist"):
        st.write("- Capture: Journal append, screenshot.")
        st.write("- Notify: Dev team via alert.")
        st.write("- Verify: Check Kafka/Redis logs.")
