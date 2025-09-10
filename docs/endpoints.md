# API Endpoints

## Django Wyckoff API

### `POST /api/pulse/wyckoff/score`
Scores Wyckoff phases and events from bar data.

**Sample payload**
```json
{
  "bars": [
    {"ts": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 1000},
    {"ts": "2024-01-01T00:01:00Z", "open": 1.1, "high": 1.3, "low": 1.0, "close": 1.2, "volume": 900}
  ]
}
```

**Expected response**
```json
{
  "score": 42.5,
  "probs": [0.1, 0.2, 0.7],
  "events": {"Spring": [false, true], "Upthrust": [false, false]},
  "reasons": ["phase=Markup"],
  "explain": {"bb_pctB": 0.0, "vol_z": 0.0, "effort_result": 0.0}
}
```

### `GET /api/pulse/wyckoff/health`
Health check for Wyckoff module.

**Sample payload**: _None_

**Expected response**
```json
{
  "status": "ok",
  "module": "wyckoff"
}
```

## MCP Server

### `GET /mcp`
Streams NDJSON events from the MCP server.

**Sample payload**: _None_

**Expected response (NDJSON stream)**
```
{"event":"open","data":{"status":"ready","timestamp":1693499999.0}}
{"event":"heartbeat","data":{"time":1693499999.0,"server":"mcp1.zanalytics.app"}}
...
```

### `GET|POST|PUT|PATCH|DELETE /exec/{full_path}`
Proxies requests to the internal Django API located at `INTERNAL_API_BASE`.

**Sample payload (POST)**
```json
{
  "example": "data"
}
```

**Expected response**
```json
{
  "status": "ok"
}
```

If the proxied endpoint returns JSON, that JSON payload is returned instead.

## Django v1 API

### `GET /api/v1/pulse/health`
Lightweight health check for the Django service.

**Sample payload**: _None_

**Expected response**
```json
{
  "status": "ok",
  "service": "django",
  "ts": "2024-01-01T00:00:00Z"
}
```

### `GET /api/pulse/health`
Readiness check that also verifies database connectivity.

**Sample payload**: _None_

**Expected response**
```json
{
  "status": "ok",
  "db": true,
  "ts": "2024-01-01T00:00:00Z"
}
```

### `GET /api/v1/account/positions`
Returns the current open positions for the account.

**Sample payload**: _None_

**Expected response**
```json
[
  {
    "ticket": 123456,
    "symbol": "EURUSD",
    "volume": 0.1
  }
]
```

### `POST /api/v1/positions/open`
Opens a new trading position.

**Sample payload**
```json
{
  "symbol": "EURUSD",
  "side": "buy",
  "volume": 0.1,
  "sl": 1.2,
  "tp": 1.3
}
```

**Expected response**
```json
{
  "ticket": 123456,
  "symbol": "EURUSD"
}
```

### `POST /api/v1/positions/close`
Closes a position fully or partially.

**Sample payload**
```json
{
  "ticket": 123456,
  "fraction": 0.5
}
```

**Expected response**
```json
{
  "ticket": 123456,
  "closed": true
}
```

### `POST /api/v1/positions/modify`
Updates stop-loss and/or take-profit for a position.

**Sample payload**
```json
{
  "ticket": 123456,
  "sl": 1.15,
  "tp": 1.35
}
```

**Expected response**
```json
{
  "ticket": 123456,
  "sl": 1.15,
  "tp": 1.35
}
```

### `POST /api/v1/positions/{ticket}/modify`
Same as above, but the ticket is provided in the path.

**Sample payload**
```json
{
  "sl": 1.15,
  "tp": 1.35
}
```

**Expected response**
```json
{
  "ticket": 123456,
  "sl": 1.15,
  "tp": 1.35
}
```

### `POST /api/v1/positions/hedge`
Places an opposite-side market order to hedge an existing position.

**Sample payload**
```json
{
  "ticket": 123456,
  "volume": 0.1
}
```

**Expected response**
```json
{
  "ticket": 123456,
  "note": "Hedge placed."
}
```
