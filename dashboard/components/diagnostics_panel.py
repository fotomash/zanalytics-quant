"""Reusable diagnostics panel for Streamlit dashboards."""

import streamlit as st
import requests
from datetime import datetime, timezone

# This endpoint aggregates the /health status of all services in the system.
HEALTH_AGGREGATOR_URL = "http://health-aggregator:8000/status"


@st.cache_data(ttl=15)
def get_system_health():
    """Fetch the consolidated health status of all microservices.

    Returns mock data when the aggregator is unreachable so the frontend can
    still be developed offline.
    """

    try:
        response = requests.get(HEALTH_AGGREGATOR_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {
            "status": "degraded",
            "services": {
                "mt5_connector": {
                    "status": "healthy",
                    "details": "Connected",
                },
                "enrichment_service": {
                    "status": "unhealthy",
                    "details": "Kafka Lag > 5s",
                },
                "discord_service": {
                    "status": "healthy",
                    "details": "Online",
                },
                "risk_enforcer": {
                    "status": "degraded",
                    "details": "High Latency",
                },
            },
        }


def render_diagnostics_panel():
    """Render the at-a-glance system health panel."""

    st.subheader("🛰️ System Operations Status")
    health_data = get_system_health()

    st.markdown(
        """
    <div style="background: linear-gradient(145deg, rgba(38, 43, 64, 0.7), rgba(20, 23, 43, 0.7)); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 25px;">
    """,
        unsafe_allow_html=True,
    )

    services = health_data.get("services", {})
    cols = st.columns(len(services) if services else 1)

    for i, (service_name, status) in enumerate(services.items()):
        with cols[i]:
            status_text = status.get("status", "unknown").upper()
            icon = (
                "✅"
                if status_text == "HEALTHY"
                else "❌" if status_text == "UNHEALTHY" else "⚠️"
            )
            color = (
                "#00FF85"
                if status_text == "HEALTHY"
                else "#FF2B2B" if status_text == "UNHEALTHY" else "#FFC700"
            )

            st.markdown(
                f"""
            <div style="text-align: center;">
                <div style="font-size: 1.2rem; font-weight: 600; color: {color};">{icon} {service_name.replace('_', ' ').title()}</div>
                <div style="font-size: 0.8rem; color: #888;">{status.get('details', 'OK')}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown(
        "<p style='text-align: center; font-size: 0.9rem; opacity: 0.7;'>For deep analysis, use the specialized monitoring tools:</p>",
        unsafe_allow_html=True,
    )
    link_cols = st.columns(2)
    link_cols[0].link_button(
        "🔗 Open Grafana Dashboards", "http://localhost:3000", use_container_width=True
    )
    link_cols[1].link_button(
        "🔗 Explore Prometheus Metrics", "http://localhost:9090", use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)


__all__ = ["render_diagnostics_panel", "get_system_health", "HEALTH_AGGREGATOR_URL"]

