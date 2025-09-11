import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

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


st.set_page_config(page_title="Diagnostics Cockpit", page_icon="🛠", layout="wide")
st.title("🛠 Diagnostics Cockpit")

# Service health
st.subheader("Service Health")
up = query_prometheus("up")
rows = [
    {"service": r.get("metric", {}).get("job", "unknown"), "status": int(r.get("value", [0, 0])[1])}
    for r in up
]
health = pd.DataFrame(rows)
if not health.empty:
    health["status"] = health["status"].map({1: "up", 0: "down"})
    st.dataframe(health, use_container_width=True)
else:
    st.info("No service metrics available")

# Kafka flow metrics
st.subheader("Kafka Flow (msg/s)")
kafka_result = query_prometheus(
    "sum(rate(kafka_server_brokertopicmetrics_messages_in_total[5m]))"
)
rate = float(kafka_result[0]["value"][1]) if kafka_result else 0.0
st.metric("Messages per second", f"{rate:.2f}")

# Cache hit ratio
st.subheader("Cache Hit Ratio")
hits = query_prometheus("sum(rate(redis_keyspace_hits_total[5m]))")
misses = query_prometheus("sum(rate(redis_keyspace_misses_total[5m]))")
h_val = float(hits[0]["value"][1]) if hits else 0.0
m_val = float(misses[0]["value"][1]) if misses else 0.0
ratio = h_val / (h_val + m_val) if (h_val + m_val) > 0 else 0.0
st.metric("Hit ratio", f"{ratio:.2%}")

# Alert summaries from Prometheus
st.subheader("Active Alerts")
alerts = query_prometheus('count(ALERTS{alertstate="firing"})')
alert_count = int(float(alerts[0]["value"][1])) if alerts else 0
st.metric("Firing alerts", alert_count)

# Recent alert logs from Loki
log_results = query_loki('{level="alert"} |~ ""', limit=5)
if log_results:
    log_rows = []
    for stream in log_results:
        for entry in stream.get("values", []):
            ts_ns, line = entry
            log_rows.append({"time": datetime.fromtimestamp(int(ts_ns) / 1e9), "log": line})
    st.table(pd.DataFrame(log_rows))
else:
    st.info("No recent alert logs")

# Navigation links
st.subheader("Drill Down")
st.markdown(f"[Alert Dashboard]({GRAFANA_URL}/d/alertmanager-dashboard)")
st.markdown(f"[Log Search]({GRAFANA_URL}/d/log-search)")
st.markdown(f"[Container Metrics]({GRAFANA_URL}/d/container-metrics)")
