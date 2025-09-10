# Streamlit ML Dashboard

Visualize live machine learning metrics stored in Redis.

## Start the app

```bash
streamlit run integration/streamlit_ml_dashboard.py
```

## Configuration

Settings can be supplied with environment variables before starting or adjusted in the Streamlit sidebar:

- `STREAMLIT_REDIS_HOST` – Redis host (default `localhost`)
- `STREAMLIT_REDIS_PORT` – Redis port (default `6379`)
- `STREAMLIT_METRIC_KEYS` – Comma-separated keys containing numeric metrics (default `ml:latency,ml:throughput`)
- `STREAMLIT_REFRESH_INTERVAL` – Refresh interval in seconds (default `5`)

The app displays the latest values found under the specified keys and refreshes automatically.
