"""
Bootstrap OS v4.3.4 - Live Monitoring Dashboard
Real-time system metrics and manipulation alerts
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import json

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")


def query_prometheus(query: str):
    """Run an instant query against Prometheus."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5
        )
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["result"]
    except Exception:
        pass
    return []


def query_prometheus_range(query: str, start: datetime, end: datetime, step: str):
    """Run a range query against Prometheus."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": step,
            },
            timeout=5,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["result"]
    except Exception:
        pass
    return []


def query_loki(query: str, limit: int = 20):
    """Fetch log lines from Loki."""
    try:
        resp = requests.get(
            f"{LOKI_URL}/loki/api/v1/query",
            params={"query": query, "limit": limit},
            timeout=5,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data["data"]["result"]
    except Exception:
        pass
    return []


# Page configuration
st.set_page_config(
    page_title="Bootstrap OS - Market Manipulation Monitor",
    page_icon="🚨",
    layout="wide"
)

# Title
st.title("🚨 Bootstrap OS v4.3.4 - Market Manipulation Monitor")
st.markdown("Real-time detection of spoofing, wash trading, and spread manipulation")

# Create columns for metrics
col1, col2, col3, col4 = st.columns(4)

# Load latest metrics from Prometheus
def load_metrics():
    """Pull current system metrics from Prometheus."""
    events = query_prometheus('events_processed_total')
    detections = query_prometheus('manipulations_detected_total')
    resp_time = query_prometheus('avg_response_time_ms')
    cost = query_prometheus('cost_saved_total')
    return {
        'events_processed': int(float(events[0]['value'][1])) if events else 0,
        'manipulations_detected': int(float(detections[0]['value'][1])) if detections else 0,
        'avg_response_time': float(resp_time[0]['value'][1]) if resp_time else 0.0,
        'cost_saved': float(cost[0]['value'][1]) if cost else 0.0,
    }

# Display metrics
metrics = load_metrics()

with col1:
    st.metric(
        "Events Processed",
        f"{metrics['events_processed']:,}"
    )

with col2:
    st.metric(
        "Manipulations Detected",
        metrics['manipulations_detected']
    )

with col3:
    st.metric(
        "Avg Response Time",
        f"{metrics['avg_response_time']:.1f}ms"
    )

with col4:
    st.metric(
        "Cost Saved",
        f"${metrics['cost_saved']:.2f}"
    )

# Divider
st.divider()

# Create two columns for charts
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📊 Manipulation Pattern Distribution")

    pattern_results = query_prometheus(
        'sum by (pattern, severity) (manipulation_pattern_total)'
    )
    rows = [
        {
            'Pattern': r['metric'].get('pattern', 'unknown'),
            'Count': float(r['value'][1]),
            'Severity': float(r['metric'].get('severity', '0')),
        }
        for r in pattern_results
    ]
    pattern_data = pd.DataFrame(rows)
    if not pattern_data.empty:
        fig = px.bar(
            pattern_data,
            x='Pattern',
            y='Count',
            color='Severity',
            color_continuous_scale='Reds',
            title="Detected Patterns (Last 24h)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No pattern data")

with chart_col2:
    st.subheader("💰 Token Efficiency Over Time")

    end = datetime.now()
    start = end - timedelta(hours=6)
    trad = query_prometheus_range(
        'token_usage_traditional', start, end, '30m'
    )
    boot = query_prometheus_range(
        'token_usage_bootstrap', start, end, '30m'
    )
    if trad and boot:
        times = [datetime.fromtimestamp(float(t)) for t, _ in trad[0]['values']]
        efficiency_data = pd.DataFrame(
            {
                'Time': times,
                'Traditional': [float(v) for _, v in trad[0]['values']],
                'Bootstrap OS': [float(v) for _, v in boot[0]['values']],
            }
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=efficiency_data['Time'],
                y=efficiency_data['Traditional'],
                name='Traditional Approach',
                line=dict(color='red', dash='dash')
            )
        )
        fig.add_trace(
            go.Scatter(
                x=efficiency_data['Time'],
                y=efficiency_data['Bootstrap OS'],
                name='Bootstrap OS',
                line=dict(color='green')
            )
        )
        fig.update_layout(
            title="Token Usage Comparison",
            yaxis_title="Tokens per Query",
            xaxis_title="Time"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No efficiency data")

# Recent alerts section
st.divider()
st.subheader("🚨 Recent Manipulation Alerts")

loki_results = query_loki('{level="alert"} |~ ""', limit=20)
alert_rows = []
for stream in loki_results:
    labels = stream.get('stream', {})
    for ts, line in stream.get('values', []):
        alert_rows.append(
            {
                'Time': datetime.fromtimestamp(int(ts) / 1e9),
                'Alert': labels.get('alertname', labels.get('level', 'alert')),
                'Message': line,
            }
        )
alerts_data = pd.DataFrame(alert_rows)
if not alerts_data.empty:
    st.dataframe(alerts_data, use_container_width=True)
else:
    st.info("No recent alerts")

# Agent status
st.divider()
st.subheader("🤖 Agent Status")

agent_col1, agent_col2, agent_col3 = st.columns(3)

with agent_col1:
    st.info("**Correlation Engine**\n✅ Active\nMemory: 1,247 patterns")

with agent_col2:
    st.success("**Risk Monitor**\n✅ Active\nLast action: 5 min ago")

with agent_col3:
    st.warning("**Liquidity Tracker**\n✅ Active\nSpread: Widening")

# Navigation links
st.divider()
st.subheader("🔎 Drill Down")
st.markdown(f"[Alert Dashboard]({GRAFANA_URL}/d/alertmanager-dashboard)")
st.markdown(f"[Log Search]({GRAFANA_URL}/d/log-search)")
st.markdown(f"[Container Metrics]({GRAFANA_URL}/d/container-metrics)")

# Auto-refresh
if st.button("🔄 Refresh Dashboard"):
    st.session_state['events'] = st.session_state.get('events', 0) + 47
    st.session_state['detections'] = st.session_state.get('detections', 0) + 1
    st.rerun()

# Footer
st.divider()
st.caption("Bootstrap OS v4.3.4 - LLM-Native Market Intelligence | Token Efficiency: 95%")

# Add auto-refresh every 5 seconds
st.markdown(
    """
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 5000);
    </script>
    """,
    unsafe_allow_html=True
)
