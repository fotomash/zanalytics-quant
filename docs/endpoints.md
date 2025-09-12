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
{"event":"heartbeat","data":{"time":1693499999.0,"server":"mcp2.zanalytics.app"}}
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

## Additional Pulse Endpoints

### `POST /api/pulse/score`
Scores bar data for confluence.

**Payload schema**
```json
{
  "bars": [
    {"ts": "string", "open": number, "high": number, "low": number, "close": number, "volume": number}
  ]
}
```

**Sample payload**
```json
{
  "bars": [
    {"ts": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 1000}
  ]

## Pulse API

### `POST /api/pulse/score`
Returns an immediate confluence score for the provided bar data.

**Sample payload**
```json
{
  "bars": [
    {"ts": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 1000}
  ]
}
```

**Expected response**
```json
{
  "score": 42.5,
  "reasons": ["phase=Markup"],
  "timestamp": "2024-01-01T00:00:00Z"

```

### `POST /api/pulse/score/peek`

Returns the current confluence score with explanations.

**Payload schema**
```json
{
  "bars": [
    {"ts": "string", "open": number, "high": number, "low": number, "close": number, "volume": number}
  ]
}
```

**Sample payload**
```json
{
  "bars": [
    {"ts": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 1000}
  ]
}
```

### `POST /api/pulse/risk/check`
Pre-trade risk evaluation.

**Payload schema**
```json
{
  "symbol": "string",
  "side": "buy|sell",
  "volume": number
}
```

**Sample payload**
```json
{
  "symbol": "EURUSD",
  "side": "buy",
  "volume": 0.1
}
```

### `GET /api/pulse/risk/summary`
Returns current risk metrics.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/pulse/risk/update`
Updates daily risk statistics.

**Payload schema**
```json
{
  "total_pnl": number,
  "trades_count": number,
  "consecutive_losses": number,
  "cooling_until": "string"
}
```

**Sample payload**
```json
{
  "total_pnl": 150.5,
  "trades_count": 3,
  "consecutive_losses": 0

Alias of `/api/pulse/score` that also returns explanation fields.

**Sample payload**
```json
{
  "bars": [
    {"ts": "2024-01-01T00:00:00Z", "open": 1.0, "high": 1.2, "low": 0.9, "close": 1.1, "volume": 1000}
  ]
}
```

**Expected response**
```json
{
  "score": 42.5,
  "reasons": ["phase=Markup"],
  "explain": {"bb_pctB": 0.0},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### `GET /api/pulse/risk/summary`
Returns the remaining daily risk and trade allowance.

**Sample payload**: _None_

**Expected response**
```json
{
  "risk_left": 100.0,
  "trades_left": 5,
  "status": "OK",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### `POST /api/pulse/risk/update`
Updates live risk statistics.

**Sample payload**
```json
{
  "total_pnl": 123.4,
  "trades_count": 2,
  "consecutive_losses": 0
}
```

**Expected response**
```json
{
  "risk_left": 87.5,
  "trades_left": 3,
  "status": "Active"
}
```

### `POST /api/pulse/risk/check`
Evaluates a proposed trade against risk rules.

**Sample payload**
```json
{
  "symbol": "EURUSD",
  "volume": 0.1,
  "side": "buy"
}
```

**Expected response**
```json
{
  "decision": "allow",
  "reasons": []

}
```

### `GET /api/pulse/signals/top`

Lists top trading signals.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/pulse/journal/recent`
Returns recent risk journal entries.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/pulse/strategy/match`
Matches the current market situation to strategies.

**Payload schema**
```json
{
  "symbol": "string"
}
```

**Sample payload**
```json
{
  "symbol": "XAUUSD"

Lists the top trading signals.

**Sample payload**: _None_

**Expected response**
```json
[
  {"symbol": "EURUSD", "score": 85, "rr": 2.1}
]
```

### `GET /api/pulse/journal/recent`
Returns recent risk journal entries.

**Sample payload**: _None_

**Expected response**
```json
[
  {
    "timestamp": "2024-01-01T00:00:00Z",
    "symbol": "EURUSD",
    "decision": "allow"
  }
]
```

### `POST /api/pulse/strategy/match`
Matches the current market situation to configured strategies.

**Sample payload**
```json
{
  "symbol": "XAUUSD"
}
```

**Expected response**
```json
{
  "strategy": "mean_reversion",
  "confidence": 0.72

}
```

### `GET /api/pulse/ticks`

Fetches recent ticks for a symbol.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/pulse/adapter/status`
MIDAS adapter health check.

**Payload schema**: _None_

**Sample payload**: _None_

## Additional v1 API Endpoints

### `POST /api/v1/protect/position`
Protect an open position via predefined actions.

**Payload schema**
```json
{
  "action": "protect_breakeven|protect_trail_50",
  "ticket": number,
  "symbol": "string",
  "lock_ratio": number
}
```

**Sample payload**
```json
{
  "action": "protect_breakeven",
  "ticket": 123456
}
```

### `POST /api/v1/trades/protect`
Alias of `/api/v1/protect/position`.

**Payload schema**
```json
{
  "action": "protect_breakeven|protect_trail_50",
  "ticket": number
}
```

**Sample payload**
```json
{
  "action": "protect_trail_50",

Fetches the latest buffered ticks for a symbol.

**Sample payload**: _None_ (use query param `symbol`)

**Expected response**
```json
{
  "symbol": "EURUSD",
  "ticks": [{"bid": 1.1, "ask": 1.2, "ts": 1699999999}]
}
```

### `GET /api/pulse/adapter/status`
Health report for the MIDAS adapter.

**Sample payload**: _None_

**Expected response**
```json
{
  "status": "up",
  "fps": 10,
  "lag_ms": 120
}
```

## Additional Django v1 Endpoints

### `GET /api/v1/ping`
Lightweight health check for the v1 API.

**Sample payload**: _None_

**Expected response**
```json
{ "status": "ok" }
```

### `POST /api/v1/protect/position`
Protect an open position by moving stop-loss or trailing profits. Alias: `POST /api/v1/trades/protect`.

**Sample payload**
```json
{
  "action": "protect_breakeven",

  "ticket": 123456
}
```

### `GET /api/v1/ping`
Simple health check.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/pulse/risk/summary`
Proxy for Pulse risk summary.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/send_market_order`
Places a market order through the trading bridge.

**Payload schema**
```json
{
  "symbol": "string",
  "volume": number,
  "order_type": "BUY|SELL",
  "sl": number,
  "tp": number
}
```


**Expected response**
```json
{ "ok": true, "ticket": 123456, "new_sl": 1.0950 }
```

### `POST /api/v1/send_market_order`
Send a market order through the MT5 bridge.


**Sample payload**
```json
{
  "symbol": "EURUSD",
  "volume": 0.1,
  "order_type": "BUY"
}
```

### `POST /api/v1/modify_sl_tp`
Modify stop-loss and take-profit for a ticket.

**Payload schema**
```json
{
  "ticket": number,
  "sl": number,
  "tp": number
}
```


  "order_type": "buy"
}
```

**Expected response**
```json
{ "trade": {"symbol": "EURUSD"}, "mutations": [] }
```

### `POST /api/v1/modify_sl_tp`
Modify stop-loss and/or take-profit for a trade ticket.


**Sample payload**
```json
{
  "ticket": 123456,
  "sl": 1.15,
  "tp": 1.35
}
```

### `GET /api/v1/symbols`
List available trading symbols.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/timeframes`
List available timeframes.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/dashboard-data`
Returns dashboard metrics.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/discipline/summary`
Summary of discipline metrics.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/positions/partial_close`
Close part of an open position.

**Payload schema**
```json
{
  "ticket": number,
  "fraction": number
}
```

  "sl": 1.10,
  "tp": 1.20
}
```

**Expected response**
```json
{ "ok": true, "result": {"ticket": 123456} }
```

### `GET /api/v1/symbols`
List symbols known to the system.

**Sample payload**: _None_

**Expected response**
```json
{ "symbols": ["EURUSD", "GBPUSD"] }
```

### `GET /api/v1/timeframes`
List available bar timeframes.

**Sample payload**: _None_

**Expected response**
```json
{ "timeframes": ["M1", "M5", "H1"] }
```

### `GET /api/v1/dashboard-data`
Aggregated dashboard payload with risk and journal snippets.

**Sample payload**: _None_

**Expected response**
```json
{
  "risk_metrics": {"trades_today": 0, "pnl_today": 0},
  "opportunities": [],
  "recent_journal": []
}
```

### `GET /api/v1/discipline/summary`
Summarises discipline metrics for the current session.

**Sample payload**: _None_

**Expected response**
```json
{ "trades_allowed": 5, "risk_left": 100.0 }
```

### `POST /api/v1/positions/partial_close`
Close a fraction of an existing position via the MT5 bridge.

**Sample payload**
```json
{
  "ticket": 123456,
  "symbol": "EURUSD",
  "fraction": 0.5
}
```

### `POST /api/v1/journal`
Create or update a journal entry for a trade.

**Payload schema**
```json
{
  "trade_id": number,
  "notes": "string"
}
```

**Sample payload**
```json
{
  "trade_id": 42,
  "notes": "Felt confident"
}
```

### `GET /api/v1/feed/balance`
Returns balance feed.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/feed/equity`
Returns equity feed.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/feed/equity/series`
Equity history series.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/equity/today`
Today's equity snapshot.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/feed/trade`
Trade feed.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/feed/behavior`
Behavior feed.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/profit-horizon`
Profit horizon analytics.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/trades/history`
Historical trades.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/trades/recent`
Recently closed trades.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/history_deals_get`
Proxy to MT5 history deals.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/history_orders_get`
Proxy to MT5 history orders.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/mirror/state`
Mirror trading state.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/market/mini`
Mini market snapshot.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/market/fetch`
Fetch public market data (e.g., VIX/DXY).

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/market/news/next`
Next scheduled news item.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/account/info`
Account information.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/journal/append`
Append a journal note.

**Payload schema**
```json
{
  "text": "string"
}
```

**Sample payload**
```json
{
  "text": "Observation"
}
```

### `GET /api/v1/journal/recent`
Recent journal entries.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/account/risk`
Account risk summary.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/account/sod`
Start-of-day account snapshot.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/orders/market`
Proxy to create market order.

**Payload schema**
```json
{
  "symbol": "string",
  "volume": number,
  "side": "buy|sell"
}
```

**Expected response**
```json
{ "ok": true }
```

### `POST /api/v1/journal`
Create or update a journal entry linked to a trade.

**Sample payload**
```json
{
  "trade_id": 1,
  "notes": "Entered on breakout"
}
```

**Expected response**
```json
{ "trade": 1, "notes": "Entered on breakout" }
```

### `GET /api/v1/feed/balance`
Publish and return account balance information.

**Sample payload**: _None_

**Expected response**
```json
{ "balance": 10000.0 }
```

### `GET /api/v1/feed/equity`
Publish and return current equity.

**Sample payload**: _None_

**Expected response**
```json
{ "equity": 10050.0 }
```

### `GET /api/v1/feed/equity/series`
Return recent equity series for charts.

**Sample payload**: _None_

**Expected response**
```json
{ "series": [[1693499999,10000.0],[1693503599,10050.0]] }
```

### `GET /api/v1/equity/today`
Return today's equity samples.

**Sample payload**: _None_

**Expected response**
```json
{ "equity": [["09:00",10000.0]] }
```

### `GET /api/v1/feed/trade`
Publish a trade feed event.

**Sample payload**: _None_

**Expected response**
```json
{ "ok": true }
```

### `GET /api/v1/feed/behavior`
Publish a behavior feed event.

**Sample payload**: _None_

**Expected response**
```json
{ "ok": true }
```

### `GET /api/v1/profit-horizon`
Return profit target horizon estimation.

**Sample payload**: _None_

**Expected response**
```json
{ "horizon_minutes": 15 }
```

### `GET /api/v1/trades/history`
Return historical trades with filters.

**Sample payload**: _None_

**Expected response**
```json
{ "trades": [] }
```

### `GET /api/v1/trades/recent`
Return most recent trades.

**Sample payload**: _None_

**Expected response**
```json
{ "trades": [] }
```

### `GET /api/v1/history_deals_get`
Proxy to MT5 history deals endpoint.

**Sample payload**: _None_

**Expected response**
```json
[]
```

### `GET /api/v1/history_orders_get`
Proxy to MT5 history orders endpoint.

**Sample payload**: _None_

**Expected response**
```json
[]
```

### `GET /api/v1/mirror/state`
Return mirror state payload for dashboard.

**Sample payload**: _None_

**Expected response**
```json
{ "state": "ok" }
```

### `GET /api/v1/market/mini`
Return mini market summary.

**Sample payload**: _None_

**Expected response**
```json
{ "symbols": [] }
```

### `GET /api/v1/market/fetch`
Fetch market data for a symbol/timeframe.

**Sample payload**: _None_ (uses query params)

**Expected response**
```json
{ "data": [] }
```

### `GET /api/v1/market/news/next`
Return next scheduled news event.

**Sample payload**: _None_

**Expected response**
```json
{ "event": "CPI", "time": "2024-01-01T12:30:00Z" }
```

### `GET /api/v1/account/info`
Return basic account information.

**Sample payload**: _None_

**Expected response**
```json
{ "balance": 10000.0, "equity": 10050.0 }
```

### `POST /api/v1/journal/append`
Append a free-form journal entry.

**Sample payload**
```json
{
  "text": "Great trade",
  "tags": ["note"]
}
```

**Expected response**
```json
{ "ok": true }
```

### `GET /api/v1/journal/recent`
Return recent journal entries.

**Sample payload**: _None_

**Expected response**
```json
{ "items": [] }
```

### `GET /api/v1/account/risk`
Current risk metrics for the account.

**Sample payload**: _None_

**Expected response**
```json
{ "risk_left": 100.0 }
```

### `GET /api/v1/account/sod`
Start-of-day snapshot for the account.

**Sample payload**: _None_

**Expected response**
```json
{ "balance": 10000.0 }
```

### `POST /api/v1/orders/market`
Proxy to MT5 market order endpoint.

**Sample payload**
```json
{
  "symbol": "EURUSD",
  "volume": 0.1,
  "side": "buy"
}
```
### `POST /api/v1/orders/modify`
Modify an existing order.

**Payload schema**
```json
{
  "order": number,
  "sl": number,
  "tp": number
}
```

**Sample payload**
```json
{
  "order": 555,
  "sl": 1.1
}
```

### `POST /api/v1/orders/close`
Close an order.

**Payload schema**
```json
{
  "order": number
}
```

**Sample payload**
```json
{
  "order": 555
}
```

### `GET /api/v1/discipline/events`
List discipline events.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/behavior/events/today`
Behavior events for today.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/discipline/event`
Append a discipline event.

**Payload schema**
```json
{
  "event": "string"
}
```

**Sample payload**
```json
{
  "event": "missed_plan"
}
```

### `GET /api/v1/market/symbols`
Market symbol metadata.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/market/calendar/next`
Next calendar event.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/market/regime`
Current market regime.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/feeds/stream`
Stream of feed updates.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/behavioral/patterns`
Detected behavioral patterns.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/journal/entry`
Create a raw journal entry.

**Payload schema**
```json
{
  "symbol": "string",
  "text": "string"
}
```

**Sample payload**
```json
{
  "symbol": "EURUSD",
  "text": "note"
}
```

### `POST /api/v1/session/set_focus`
Set current session focus.

**Payload schema**
```json
{
  "symbol": "string"
}
```

**Sample payload**
```json
{
  "symbol": "XAUUSD"
}
```

### `GET /api/v1/positions/{ticket}/protect`
Suggest protection options for a ticket.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/user/prefs`
Retrieve user preferences.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/user/prefs`
Update user preferences.

**Payload schema**
```json
{
  "favorite_symbol": "string"
}
```

**Sample payload**
```json
{
  "favorite_symbol": "EURUSD"
}
**Expected response**
```json
{ "ticket": 123456 }
```

### `POST /api/v1/orders/modify`
Proxy to MT5 order modification endpoint.

**Sample payload**
```json
{
  "ticket": 123456,
  "sl": 1.10,
  "tp": 1.20
}
```

**Expected response**
```json
{ "ok": true }
```

### `POST /api/v1/orders/close`
Proxy to MT5 order close endpoint.

**Sample payload**
```json
{ "ticket": 123456 }
```

**Expected response**
```json
{ "closed": true }
```

### `GET /api/v1/discipline/events`
List discipline events recorded for today.

**Sample payload**: _None_

**Expected response**
```json
{ "events": [] }
```

### `GET /api/v1/behavior/events/today`
Return today's behavior events.

**Sample payload**: _None_

**Expected response**
```json
{ "events": [] }
```

### `POST /api/v1/discipline/event`
Append a discipline event.

**Sample payload**
```json
{
  "ts": "2024-01-01T00:00:00Z",
  "type": "profit_milestone"
}
```

**Expected response**
```json
{ "ok": true }
```

### `GET /api/v1/market/symbols`
List tradable market symbols.

**Sample payload**: _None_

**Expected response**
```json
{ "symbols": ["EURUSD"] }
```

### `GET /api/v1/market/calendar/next`
Return next economic calendar event.

**Sample payload**: _None_

**Expected response**
```json
{ "event": "NFP", "time": "2024-01-05T13:30:00Z" }
```

### `GET /api/v1/market/regime`
Return current market regime classification.

**Sample payload**: _None_

**Expected response**
```json
{ "regime": "trending" }
```

### `GET /api/v1/feeds/stream`
Server-sent events stream for feed data.

**Sample payload**: _None_

**Expected response (NDJSON stream)**
```
{"event":"open"}
```

### `GET /api/v1/behavioral/patterns`
Return detected behavioral patterns.

**Sample payload**: _None_

**Expected response**
```json
{ "patterns": [] }
```

### `POST /api/v1/journal/entry`
Append a single journal entry.

**Sample payload**
```json
{
  "ts": "2024-01-01T00:00:00Z",
  "text": "Observation"
}
```

**Expected response**
```json
{ "ok": true }
```

### `POST /api/v1/session/set_focus`
Set the current session focus item.

**Sample payload**
```json
{ "symbol": "EURUSD" }
```

**Expected response**
```json
{ "ok": true }
```

### `GET /api/v1/positions/<ticket>/protect`
Suggest protection options for a position.

**Sample payload**: _None_

**Expected response**
```json
{ "actions": [{"label": "Move SL to BE"}] }
```

### `GET /api/v1/user/prefs`
Retrieve stored user preferences.

**Sample payload**: _None_

**Expected response**
```json
{ "favorite_symbol": "EURUSD" }
```

### `POST /api/v1/user/prefs`
Update user preferences.

**Sample payload**
```json
{ "favorite_symbol": "EURUSD" }
```

**Expected response**
```json
{ "ok": true, "favorite_symbol": "EURUSD" }
```

### `POST /api/v1/playbook/session-init`
Initialize a playbook session.

**Payload schema**
```json
{
  "n_strategies": number
}
```

**Sample payload**
```json
{
  "n_strategies": 3
}
```

### `GET /api/v1/liquidity/map`
Liquidity map for a symbol.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/opportunity/priority-items`
Rank candidate symbols.

**Payload schema**
```json
{
  "candidates": [
    {"symbol": "string"}
  ]
}
```

**Sample payload**
```json
{
  "candidates": [{"symbol": "EURUSD"}, {"symbol": "XAUUSD"}]
}
```

### `POST /api/v1/ai/explain-signal`
Explain a trading signal.

**Payload schema**
```json
{
  "signal": "string"
}
```

**Sample payload**
```json
{
  "signal": "Bullish breakout"
}
```

### `GET /api/v1/report/daily-summary`
Daily performance summary.

**Payload schema**: _None_

**Sample payload**: _None_

### `GET /api/v1/state/snapshot`
Combined state snapshot for dashboards.

**Payload schema**: _None_

**Sample payload**: _None_

### `POST /api/v1/actions/query`
Unified actions bus for read and write operations.

**Payload schema**
```json
{
  "type": "string",
  "payload": {}
}
```

**Sample payload**
```json
{ "type": "session_boot", "payload": { "user_id": "demo" } }

Query consolidated actions via the Actions Bus.

**Required headers**: `Content-Type: application/json`

**Sample payload**
```json
{
  "type": "session_boot",
  "payload": {"user_id": "demo"}
}
```

### `GET /api/v1/liquidity/map`
Return a liquidity map snapshot.

**Sample payload**: _None_

**Expected response**
```json
{ "levels": [] }
```

### `GET /api/v1/opportunity/priority-items`
Return prioritized opportunity items.

**Sample payload**: _None_

**Expected response**
```json
{ "items": [] }
```

### `POST /api/v1/ai/explain-signal`
Explain a trading signal using AI.

**Sample payload**
```json
{ "signal": "buy EURUSD" }
```

**Expected response**
```json
{ "explanation": "Volume surge" }
```

### `GET /api/v1/report/daily-summary`
Return a daily summary report.

**Sample payload**: _None_

**Expected response**
```json
{ "summary": {} }
```

### `GET /api/v1/state/snapshot`
Return a snapshot of current system state.

**Sample payload**: _None_

**Expected response**
```json
{ "state": {} }
```


### `POST /api/v1/actions/query`
Query available actions via the Actions Bus.

**Required headers**: `Content-Type: application/json`

**Sample payload**
```json
{ "type": "session_boot", "payload": {"user_id": "demo"} }
```

**Expected response**
```json
{ "actions": [] }
```
 

### `GET /api/v1/openapi.actions.yaml`
Serve a slim OpenAPI specification for the Actions endpoints.

**Sample payload**: _None_

**Expected response**
```yaml
openapi: 3.0.0
```

