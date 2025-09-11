# Streamlit ML Dashboard

Visualize time-series ML metrics and current risk indicators published by the
Redis ML bridge.

## Start the app

Run directly:
```bash
streamlit run dashboard/ml_dashboard.py
```

Or use the make recipe:
```bash
make ml-dashboard
```

## Configuration

Settings can be provided via environment variables before starting or adjusted
in the Streamlit sidebar:

- `STREAMLIT_REDIS_HOST` – Redis host (default `localhost`)
- `STREAMLIT_REDIS_PORT` – Redis port (default `6379`)
- `ML_SIGNAL_STREAM` – Redis stream carrying full model outputs (default `ml:signals`)
- `ML_RISK_STREAM` – Redis stream carrying risk updates (default `ml:risk`)
- `STREAMLIT_REFRESH_INTERVAL` – Refresh interval in seconds (default `5`)

Use the sidebar to select which metrics to plot and how often the dashboard
should refresh. The app renders time-series charts and displays the most recent
risk values for each symbol.
