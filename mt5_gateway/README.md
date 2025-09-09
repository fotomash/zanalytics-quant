MT5 Gateway (FastAPI)

Overview
- Co-located FastAPI gateway for MetaTrader5 inside the MT5 container.
- Exposes endpoints for account/positions and trading actions:
  - GET /health, GET /routes
  - GET /account_info, GET /positions_get
  - POST /send_market_order
  - POST /partial_close_v2, POST /partial_close, POST /close_position

Repository Layout
- app.py: FastAPI application.
- requirements.txt: pinned runtime deps.
- supervisord.conf: example program section if using supervisord.

How It’s Wired Here
- docker-compose mounts this directory into the MT5 container at /opt/mt5_gateway (read-only).
- The MT5 container already runs a Flask MT5 API on port 5001 via Wine Python.
- To avoid conflicts, the FastAPI gateway is disabled by default and, when enabled, uses port 5002 by default.

Enable the Gateway (optional)
1) Set environment variables for the mt5 service (e.g. in .env or the service environment block):
   - ENABLE_MT5_GATEWAY=1
   - MT5_GATEWAY_PORT=5002   # optional, defaults to 5002

2) Recreate or restart the mt5 container:
   - docker compose up -d mt5

Internals
- backend/mt5/scripts/07-start-wine-flask.sh will:
  - keep running the existing Flask API at port 5001 (Wine Python), and
  - if ENABLE_MT5_GATEWAY=1 and /opt/mt5_gateway/app.py exists, it will:
    - install /opt/mt5_gateway/requirements.txt into Wine Python (non-fatal if already satisfied)
    - start uvicorn for mt5_gateway on 0.0.0.0:${MT5_GATEWAY_PORT:-5002}

Notes
- If you prefer to run the gateway under Linux Python with supervisord instead of Wine Python, use supervisord.conf and start uvicorn from Linux Python. Ensure MetaTrader5 is importable in that environment (varies by setup).
- Django and other services can target the gateway by setting MT5_URL or MT5_API_URL accordingly, e.g. http://mt5:5002 if you enable this module.

