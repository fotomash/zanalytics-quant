# Dashboard Module

The `dashboard/` directory hosts the primary Streamlit application for Zanalytics. It bundles risk, pulse and utility views into a single multi‑page app.

## Entry Points
- `Home.py` – main launcher that wires the pages.
- `pulse_dashboard.py` and `pulse_kernel_dashboard.py` – focused dashboards for pulse analytics.
- `wiki_dashboard.py` – streamlit wrapper around internal wiki data.
- `cluster_viz.py` – explore enriched vectors with UMAP/t‑SNE and Whisperer queries.
- `pages/system_diagnostics.py` – aggregates health checks for Redis, Kafka, MT5 and the Django API.
- `stream.py` – minimal WebSocket stream viewer for MCP2.

Launch the default app with:

```bash
streamlit run dashboard/Home.py
```

## Setup
1. **Install dependencies** (from repo root):
   ```bash
   pip install -r requirements/dashboard.txt  # or dashboard/requirements.txt
   ```
   This pulls in core analytics libraries like `scikit-learn` and `umap-learn` needed for local development.
2. **Environment** – ensure Redis and the Django API are reachable; most pages expect live data. Set `HEALTH_AGGREGATOR_URL` to the base URL of your health aggregator service.

## Customization
- Add or modify Streamlit pages inside `pages/`.
- Share common UI components via the `components/` package.
- Update configuration values under `config/` or `configs/`.

### Clustering Prototype

A standalone clustering view lives under `_mix/4_〽️ Comprehensive Market Analysis.py_`.
Run it directly:

```bash
streamlit run dashboard/_mix/4_〽️\ Comprehensive\ Market\ Analysis.py_
```

The page groups volatility regimes and price levels.  See
[docs/clustering_dashboard.md](../docs/clustering_dashboard.md) for more details.

## Maintenance Notes
- Keep `requirements/dashboard.txt` in sync with `dashboard/requirements.txt`.
- Watch for breaking Streamlit or API changes and update entry points accordingly.
- Run `streamlit run` locally before pushing changes to catch obvious errors.

## System Diagnostics

The **System Diagnostics** page surfaces health indicators for core services
using the existing `dashboards/diagnose.py` helpers and the
`diagnose_and_fix.sh` remediation script. Run it directly with:

```bash
streamlit run dashboard/pages/system_diagnostics.py
```

Within the main app, launch `Home.py` and navigate to *System Diagnostics*
from the sidebar. Failed checks include links to relevant Docker logs and the
remediation script for quick troubleshooting.

For more information see the [project docs](../docs/README.md).

## Deployment Notes
- Live metrics now stream over a WebSocket connection.
- When deploying behind a reverse proxy (e.g., Nginx or Traefik), be sure to enable WebSocket upgrades. For Nginx:
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```
- Configure the WebSocket endpoint via the `LIVE_DATA_WS_URL` environment variable.
