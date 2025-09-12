"""Diagnostics Cockpit page."""

from __future__ import annotations

import streamlit as st

from metrics.prometheus import fetch_metrics
from utils.docs import load_markdown_docs
from utils.health import fetch_service_health


st.set_page_config(page_title="Diagnostics Cockpit", layout="wide")

st.title("Diagnostics Cockpit")

st.subheader("Service Health")
health = fetch_service_health()
if health:
    rows = "".join(
        f"<tr><td>{name}</td><td><span style='background-color:{'green' if ok else 'red'};color:white;padding:2px 6px;border-radius:4px'>{'HEALTHY' if ok else 'UNHEALTHY'}</span></td></tr>"
        for name, ok in health.items()
    )
    table_html = (
        "<table><thead><tr><th>Service</th><th>Status</th></tr></thead><tbody>"
        + rows
        + "</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("No service health data available.")

cols = st.columns(2)
with cols[0]:
    st.subheader("Key Metrics")
    metrics = fetch_metrics()
    for label, value in metrics.items():
        st.metric(label, f"{value:.2f}")

with cols[1]:
    st.subheader("Documentation")
    docs = load_markdown_docs()
    if docs:
        tabs = st.tabs(list(docs.keys()))
        for tab, (name, content) in zip(tabs, docs.items()):
            with tab:
                st.markdown(content)
    else:
        st.write("No documentation found.")
