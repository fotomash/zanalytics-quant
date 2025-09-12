# LLM Integration Guide (The_Whisperer)

This guide documents the agent‑facing Actions Bus, key REST endpoints, session semantics (SoD), and operational notes so LLMs can interact with Zanalytics Pulse safely and consistently.

## Base URLs
- Primary API: `https://mcp2.zanalytics.app`
- Slim Actions Spec (OpenAPI): `https://mcp2.zanalytics.app/openapi.actions.yaml`

## Actions Bus
- Endpoint: `POST /api/v1/actions/query`
- Body: `{ "type": string, "payload": object }`
- Verbs (current):
  - `trades_recent` → returns array of TradeItem
  - `whisper_suggest` → returns `{ message, heuristics, meta }`
- See `docs/gpt_llm/actions_bus.md` for payloads and examples.

## Key REST Endpoints
- Recent trades: `GET /api/v1/trades/recent?limit=N`
- Trade history (no `limit`): `GET /api/v1/trades/history`
- Positions: `GET /api/v1/account/positions`
- Risk envelope: `GET /api/v1/account/risk`
- Intraday equity: `GET /api/v1/equity/today`
- Behavior events: `GET /api/v1/behavior/events/today`
- Pulse bars (price confirmation): `GET /api/v1/feed/bars-enriched?symbol={SYM}&timeframe=M15&limit=1`
- Market mini header (VIX/DXY): `GET /api/v1/market/mini`

## Session Semantics (SoD)
- Trading day SoD anchors to 23:00 `Europe/London` (configurable):
  - `PULSE_SESSION_TZ` (default `Europe/London`)
  - `PULSE_SESSION_CUTOFF_HOUR` (default `23`)
- Today’s `sod_equity` is derived from previous session close; cached in Redis: `sod_equity:{YYYYMMDD}`.
- Overrides:
  - Redis override: `sod_equity_override:{YYYYMMDD}`
  - Env demo override: `SOD_EQUITY_OVERRIDE`
  - API: `POST /api/v1/account/sod` to set/clear per‑day overrides

## VIX/DXY Availability
- `/api/v1/market/mini` returns VIX/DXY sparklines when either:
  - DB bars exist for symbols `VIX`/`DXY`, or
  - Redis caches are present: `market:vix:series`, `market:dxy:series`
- Seed caches if empty:
  - `GET /api/v1/market/fetch` (Yahoo 1d/5m); schedule every 5 minutes in production

## Whisper Suggestion Flow
- LLMs should call the Actions Bus:
  ```json
  POST /api/v1/actions/query
  { "type": "whisper_suggest", "payload": { "symbol": "XAUUSD", "user_id": "local" } }
  ```
- Response:
  ```json
  { "message": "one short suggestion", "heuristics": [ { ... } ], "meta": { "user_id": "local", "symbol": "XAUUSD" } }
  ```
- Cooldowns are enforced server‑side per user (keys: `{user_id}:{category}`) to avoid spam.

## Price Integrity (Hard Rule)
- Never fabricate prices; confirm from `/api/v1/feed/bars-enriched?limit=1`.
- If feeds are unavailable, state uncertainty and proceed without quoting numbers.

## Error Handling Patterns
- If a verb rejects an unknown parameter (e.g., `limit` on `/trades/history`), retry with the documented form or use the bus.
- Prefer Actions Bus for portable, schema‑stable calls.

## Discord Sends
- LLMs should NOT call Discord directly. The backend handles posting; return human‑readable text.
- Previous alert integrations are deprecated; Discord is the supported messaging platform.

## Security
- Current endpoints are unauthenticated; if `X-Pulse-Key` appears, include it.

## Changelog
- 0.1.0
  - Added Actions Bus `trades_recent`, `whisper_suggest`
  - Documented SoD session anchor and overrides
  - Added VIX/DXY cache seeding guidance

