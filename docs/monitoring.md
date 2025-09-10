# Monitoring

This project uses a Prometheus, Grafana, and Alertmanager stack to observe
application and infrastructure health.

## Prometheus scraping

Prometheus pulls metrics from application services, the host node, and running
containers. Each component exposes a `/metrics` endpoint. Prometheus scrapes
these endpoints at regular intervals and stores the results in its time‑series
database for querying and alert evaluation.

## Grafana dashboards

Grafana connects to Prometheus as a data source. Prebuilt dashboards visualize
node statistics, container performance, and application metrics. The Grafana UI
is available at `http://localhost:3000`, and additional dashboards can be added
or customized to suit operational needs.

## Alertmanager behavior

Prometheus rules evaluate metrics and fire alerts when conditions are met.
Alertmanager receives these alerts, groups and de‑duplicates them, and routes
notifications to configured receivers such as the Uncomplicated Alert Receiver
UI. Alerts persist until the triggering condition clears or they are
acknowledged.

