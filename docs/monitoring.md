# Monitoring

This project uses a Prometheus, Grafana, Alertmanager, Loki, and Promtail stack
to observe application and infrastructure health.

```
metrics: services -> Prometheus -> Grafana -> Alertmanager
logs:    containers -> Promtail -> Loki -> Grafana
```

## Prometheus scraping

Prometheus pulls metrics from application services, the host node, and running
containers. Each component exposes a `/metrics` endpoint. Prometheus scrapes
these endpoints at regular intervals and stores the results in its time‑series
database for querying and alert evaluation.

## Grafana dashboards

Grafana connects to Prometheus and Loki as data sources. Prebuilt dashboards
visualize node statistics, container performance, application metrics, and
centralized logs. The Grafana UI is available at `http://localhost:3000`, and
additional dashboards can be added or customized to suit operational needs.

### Diagnostics Cockpit

`dashboard/diagnostics_cockpit.py` provides a Streamlit view that combines
service health checks, Kafka throughput, cache hit ratios, and alert summaries.
Run it locally with:

```
PROMETHEUS_URL=http://localhost:9090 \
LOKI_URL=http://localhost:3100 \
GRAFANA_URL=http://localhost:3000 \
streamlit run dashboard/diagnostics_cockpit.py
```

Links in the cockpit jump to the Alertmanager, log search, and container metric
dashboards for deeper investigation.

## Log pipeline

Promtail tails container logs and forwards them to Loki for centralized
storage. The configuration at `monitoring/configs/promtail/promtail.yaml`
targets containers labeled with `logging=promtail`, exposes metrics on
`http://localhost:9080`, and pushes log entries to `http://loki:3100`. Loki's
API is reachable at `http://localhost:3100`, and logs can be explored in
Grafana's **Explore** view at `http://localhost:3000` using the Loki data
source.

## Alertmanager behavior

Prometheus rules evaluate metrics and fire alerts when conditions are met.
Alertmanager receives these alerts, groups and de‑duplicates them, and routes
notifications to configured receivers such as the Uncomplicated Alert Receiver
UI. Alerts persist until the triggering condition clears or they are
acknowledged.

The Streamlit monitoring view at `dashboard/_mix/monitoring_dashboard.py` now
pulls its metrics and recent alerts directly from Prometheus and Loki to avoid
stale placeholder data.

