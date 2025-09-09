# Zanalytics Pulse – Realtime Helpers and GPT Actions

This package provides a tiny Redis-backed realtime utility module for the Pulse stack and a concise OpenAPI schema suitable for GPT Actions.

## Install (editable)

From the repo root:

```
pip install -e .
```

This exposes the `pulse` package with a small client wrapper and Redis helpers.

## Usage – PulseClient

```
from pulse.client import PulseClient

pc = PulseClient()

# Publish a whisper (appends to list and publishes on a channel)
pc.publish_whisper({
    "id": "w-001",
    "ts": 1725705600,
    "category": "risk",
    "severity": "warn",
    "message": "Risk budget usage at 80%.",
    "reasons": [{"key": "risk_used_pct", "value": 0.80}],
})

# Start a cross-process cooldown (returns True only once until TTL expires)
if pc.start_cooldown("risk.budget.high", 600):
    # First time in 10 minutes
    ...

# Seen-once dedupe (returns True only once per TTL window)
if pc.seen_once("event:profit_milestone", ttl_seconds=300):
    ...
```

These helpers fail gracefully if Redis is unavailable (they return False/True as documented) so they can be used in dev without extra plumbing.

## GPT Actions – OpenAPI

The repository includes an `openapi.yaml` describing read/write endpoints that the dashboard and the bot use. Point your GPT Action configuration to this file or paste its contents and set the server URL appropriately.

Key paths:

- `GET /api/v1/market/mini` – VIX/DXY sparklines + regime + next news stub
- `GET /api/v1/mirror/state` – Behavioral mirror state (discipline, patience, efficiency, conviction, pnl_norm)
- `GET /api/v1/discipline/summary` – Today/yesterday/7‑day discipline + events
- `GET /api/v1/profit-horizon?limit=20` – Profit Horizon data (ghost bars)
- `GET /api/v1/account/positions` – Normalized open positions from MT5 bridge (safe fallback [])
- `GET /api/pulse/whispers` – Latest whispers
- `POST /api/pulse/whisper/ack` – Acknowledge a whisper
- `POST /api/pulse/whisper/act` – Journal act intent
- `GET /api/pulse/whispers/log` – Human-readable whisper timeline

Optional market utilities:

- `GET /api/v1/market/fetch` – Fetch ^VIX/^DXY (cached)
- `POST /api/v1/market/news/next` – Set next high-impact news in Redis

> Auth
>
> No authentication is required by default. An `X-Pulse-Key` header may be introduced later without breaking the contract.

## Dev Notes

- Package metadata is defined in `pyproject.toml`. Only the `pulse` package is exported.
- The OpenAPI file is intentionally minimal and focused on the Whisperer stack.
- If you add more services that need Redis helpers, depend on `zanalytics-pulse` and import `pulse.client.PulseClient`.

## License

Proprietary – © Zanalytics.


Return to [main README](README.md)
