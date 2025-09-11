# Pulse API

This service exposes core features of the Pulse runtime over HTTP. It wraps the
`PulseKernel` in a small FastAPI application so other components can interact
with scoring, risk management, and journaling capabilities.

## FastAPI shim

The API layer is intentionally minimal. It acts as a lightweight shim around
`PulseKernel`, allowing multiple services to share the same runtime while keeping
third-party dependencies to a minimum.

## Available endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/pulse/health` | Service health check and kernel status. |
| `POST` | `/pulse/score` | Score a market symbol for a given timeframe. |
| `POST` | `/pulse/risk` | Evaluate whether a trade signal is allowed. |
| `POST` | `/pulse/journal` | Append an entry to the journal. |
| `GET` | `/pulse/journal/recent` | Fetch recent journal entries from Redis. |

## Authentication

All mutating and data endpoints are protected by a simple API key. Set the
`PULSE_API_KEY` environment variable when starting the service and include the
same value in requests using the `X-API-Key` header:

```bash
export PULSE_API_KEY="secret123"
uvicorn services.pulse_api.main:app --reload

# Example request
curl -H "X-API-Key: secret123" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "EURUSD"}' \
     http://localhost:8000/pulse/score
```

## Environment variables

- **`PULSE_CONFIG`** – Path to the Pulse configuration file. Defaults to
  `pulse_config.yaml` when unset.
- **`PULSE_API_KEY`** – API key required for authorized requests. Requests must
  supply this value in the `X-API-Key` header.

## Local development

Install dependencies and launch the API using Uvicorn:

```bash
pip install -r services/pulse_api/requirements.txt
uvicorn services.pulse_api.main:app --reload
```

## API version

Current API version: **1.0.0**.

