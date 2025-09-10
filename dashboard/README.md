# Dashboard Module

The `dashboard/` directory hosts the primary Streamlit application for Zanalytics. It bundles risk, pulse and utility views into a single multi‑page app.

## Entry Points
- `Home.py` – main launcher that wires the pages.
- `pulse_dashboard.py` and `pulse_kernel_dashboard.py` – focused dashboards for pulse analytics.
- `wiki_dashboard.py` – streamlit wrapper around internal wiki data.

Launch the default app with:

```bash
streamlit run dashboard/Home.py
```

## Setup
1. **Install dependencies** (from repo root):
   ```bash
   pip install -r requirements-dashboard.txt  # or dashboard/requirements.txt
   ```
2. **Environment** – ensure Redis and the Django API are reachable; most pages expect live data.

## Customization
- Add or modify Streamlit pages inside `pages/`.
- Share common UI components via the `components/` package.
- Update configuration values under `config/` or `configs/`.

## Maintenance Notes
- Keep `requirements-dashboard.txt` in sync with `dashboard/requirements.txt`.
- Watch for breaking Streamlit or API changes and update entry points accordingly.
- Run `streamlit run` locally before pushing changes to catch obvious errors.

For more information see the [project docs](../docs/README.md).
