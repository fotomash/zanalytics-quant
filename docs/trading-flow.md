Trading Flow via /exec
======================

Overview
--------

- External clients call the MCP server's `/exec/{full_path}` endpoint.
- The MCP server forwards the request to the internal Django API at `INTERNAL_API_BASE/{full_path}`.
- When the path is `api/v1/positions/modify`, the request modifies an existing position's SL or TP.

/exec to Django position modify
-------------------------------

Example: modify stop loss and take profit for a ticket.

```bash
curl -sX POST "$MCP/exec/api/v1/positions/modify" \
  -H 'Content-Type: application/json' \
  -d '{"ticket":302402468,"sl":3625,"tp":3627}'
```

The MCP proxy removes the `/exec` prefix and forwards:

- Method: POST
- URL: `$INTERNAL_API_BASE/api/v1/positions/modify`
- Body: `{ "ticket": 302402468, "sl": 3625, "tp": 3627 }`

If the Django endpoint returns JSON, that JSON is relayed back to the caller. Non‑JSON payloads are wrapped with `{ "status": "ok" }`.

Session boot parameters
-----------------------

The `session_boot` action composes a snapshot of recent trading activity. It is typically invoked via:

```bash
curl -sX POST "$MCP/exec/api/v1/actions/query" \
  -H 'Content-Type: application/json' \
  -d '{"type":"session_boot","payload":{"limit_trades":10,"include_positions":true}}'
```

Payload fields:

- `limit_trades`: maximum number of recent trades to include (default 10).
- `include_positions`: when `true`, include open positions in the response.
- `include_equity`: include balance and drawdown summary (default true).
- `include_risk`: include risk environment summary (default true).

The Django view honours these flags when assembling the response.

