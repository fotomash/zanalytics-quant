Actions Verbs Catalog
=====================

This catalog documents each verb exposed via the single Actions endpoint:
- Endpoint: `POST /api/v1/actions/query`
- Schema: `openapi.actions.yaml`

Conventions
- All requests are JSON: `{ "type": "<verb>", "payload": { ... } }`
- All responses are JSON. Unless specified, responses are direct passthroughs from the underlying Django views.

Index
- Positions: position_open, position_close, position_modify, position_hedge
- Account/State: session_boot, state_snapshot, account_info, account_positions, account_risk, equity_today
- Market/Scan: market_mini, market_snapshot, market_symbols, market_calendar_next, market_regime, liquidity_map, pulse_status, opportunity_priority_items
- Journal/Behavior: journal_recent, journal_append, behavior_events, whisper_suggest
- Auth: mcp2_authenticate

Positions

position_open
- Payload
  - symbol: string (e.g., "XAUUSD")
  - volume: number (lots)
  - side: string ("buy" | "sell")
  - sl: number, optional (price)
  - tp: number, optional (price)
  - comment: string, optional
- Response
  - { ok: boolean, order: { ... MT5 order result ... } }
- Example
```json
{ "type": "position_open", "payload": { "symbol": "XAUUSD", "volume": 0.10, "side": "buy", "sl": 0, "tp": 0 } }
```

position_close
- Payload
  - ticket: integer
  - fraction: number in (0,1), optional
  - volume: number (lots), optional; if provided it overrides fraction
- Response
  - { ok|success: true, result: { ... } }
- Notes
  - Defaults to full close when neither fraction nor volume is provided.
- Example
```json
{ "type": "position_close", "payload": { "ticket": 302402468, "fraction": 0.5 } }
```

position_modify
- Payload
  - ticket: integer
  - sl: number, optional (price)
  - tp: number, optional (price)
- Response
  - { ok: true, result: { ... } }
- Example
```json
{ "type": "position_modify", "payload": { "ticket": 302402468, "sl": 3625 } }
```

position_hedge
- Payload
  - ticket: integer
  - volume: number, optional (defaults to current position volume)
- Response
  - { ok|success: true, result: { ... }, note?: "..." }
- Notes
  - On netting accounts, hedge nets exposure; response contains a note.
- Example
```json
{ "type": "position_hedge", "payload": { "ticket": 302402468, "volume": 0.10 } }
```

Account / State

session_boot
- Payload
  - limit_trades: integer, optional (default 10)
  - include_positions: boolean, optional (default true)
  - include_equity: boolean, optional (default true)
  - include_risk: boolean, optional (default true)
- Response
  - { trades: [...], positions: [...], equity: {...}|null, risk: {...}|null }

state_snapshot
- Payload: none
- Response
  - { mirror: {...}, patterns: {...}, risk: {...}, equity: {...} }

account_info
- Payload: none
- Response: normalized MT5 account info

account_positions
- Payload: none
- Response: list of open positions (broker-normalized)

account_risk
- Payload: none
- Response: session risk envelope (target/loss caps, exposure, used pct)

equity_today
- Payload: none
- Response: session equity stats

Market / Scan

market_mini
- Payload: none
- Response: { vix: {series,value}, dxy: {series,value}, news: {...}, regime: string }
- Synonym: `market_snapshot`

market_symbols
- Payload: none
- Response: { symbols: ["XAUUSD", ...] }

market_calendar_next
- Payload
  - limit: integer, optional (default 5)
- Response: array of events { ts, label, importance, currency }

market_regime
- Payload: none
- Response: { regime: string, ... }

liquidity_map
- Payload
  - symbol: string, optional
  - timeframe: string, optional (e.g., "M5")
- Response: { asof, levels: [{ price, kind, strength }] }

pulse_status
- Payload
  - symbol: string (default "XAUUSD")
- Response: { context, liquidity, structure, imbalance, risk, wyckoff, confluence }

opportunity_priority_items
- Payload
  - candidates: array, optional
  - symbols: array, optional
  - constraints: object, optional
- Response: { items: [{ symbol, priority, reason }] }

Journal / Behavior

journal_recent
- Payload
  - limit: integer, optional (default 50)
- Response: array of recent entries { id, ts, trade_id, text }

journal_append
- Payload
  - trade_id: integer, required (current impl.)
  - kind: string (ENTRY|CLOSE|PARTIAL_CLOSE|HEDGE|ORDER_MODIFY), default "note"
  - text: string
  - tags: array[string], optional
  - meta: object, optional
- Response: { ok: true, id, ts }

behavior_events
- Payload: none
- Response: array of today's events { ts, type, weight, explain }

whisper_suggest
- Payload
  - user_id: string, optional
  - symbol: string, optional (default XAUUSD)
- Response: { message: string|null, heuristics: [...], meta: { user_id, symbol } }

Auth / MCP1

mcp2_authenticate
- Payload
  - token: string
- Response
  - { status: string }

Notes on idempotency
- Send `X-Idempotency-Key` header on mutating actions (open/close/modify/hedge, journal_append) to dedupe retries.

