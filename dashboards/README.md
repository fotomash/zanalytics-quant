# Dashboard Prototypes

The `dashboards/` directory collects standalone Streamlit scripts and experiments. These examples are not part of the main `dashboard/` app but provide templates or diagnostics.

## Contents
- `diagnose.py` – quick diagnostic dashboard used for troubleshooting services.

## Setup
1. Install the shared dashboard dependencies:
   ```bash
   pip install -r requirements/dashboard.txt
   ```
2. Ensure any required services (e.g. Redis, Django API) are running.

## Running an Example
Execute a script directly with Streamlit. For example:

```bash
streamlit run dashboards/diagnose.py
```

## Maintenance Notes
- Scripts here may drift or be deprecated; promote stable ones into `dashboard/`.
- Keep imports and API clients aligned with the main application.

See the core dashboards under [dashboard/](../dashboard/README.md).
