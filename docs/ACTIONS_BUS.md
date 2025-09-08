Zanalytics Actions Bus (Slim)
================================

Purpose
- Provide a single, GPT-friendly endpoint that exposes many actions as verbs in the request body.
- Keep the public Actions OpenAPI under the 30-operation cap without losing breadth.

Authoritative schema
- File to upload to Custom GPT: `openapi.actions.yaml`
- Endpoint: `POST /api/v1/actions/query`
- Request shape (object schema required by GPT):
  {
    "type": "<verb>",
    "payload": { ... }
  }
  Note: The spec includes rich per-verb payload schemas, but to satisfy GPT’s function export
  requirements the requestBody references an object schema (`ActionQueryRequest`).

Where verbs are routed
- Server: `backend/django/app/nexus/views.py` → `ActionsQueryView.post()`
- Each `if typ == '<verb>'` branch maps to an existing Django view or proxy.

Current verbs (2025-09-08)
- State and account
  - `session_boot` → composite snapshot (trades, positions, equity, risk)
  - `state_snapshot` → minimal state (mirror, patterns, risk, equity)
  - `account_info` → normalized MT5 account info
  - `account_positions` → open positions proxy
  - `account_risk` → session risk envelope
  - `equity_today` → session equity metrics
- Market/monitoring
  - `market_mini` → header snapshot (VIX/DXY/news/regime)
  - `market_symbols` → available symbols
  - `market_calendar_next` → next high-impact events (payload: {limit})
  - `market_regime` → current regime
  - `liquidity_map` → levels by symbol/timeframe (payload: {symbol, timeframe})
  - `opportunity_priority_items` → ranking (payload passthrough)
- Journal/behavior
  - `journal_recent` → last N entries (payload: {limit})
  - `journal_append` → append entry (payload forwarded)
  - `whisper_suggest` → Whisperer summary given current state
- Positions/trading
  - `position_open` → open market order (payload: {symbol, volume, side, sl?, tp?, comment?})
  - `position_close` → full/partial close (payload: {ticket, fraction? | volume?})
  - `position_modify` → modify SL/TP (payload: {ticket, sl?, tp?})
  - `position_hedge` → open opposite-side order (payload: {ticket, volume?})

Response shapes
- Vary by verb; most are direct passthroughs from their Django view.
- Position operations return `{ ok|success: true, result|order: {...} }` on success.

Examples
- Close half a position
  curl -sX POST "$DJANGO/api/v1/actions/query" \
    -H 'Content-Type: application/json' \
    -d '{"type":"position_close","payload":{"ticket":302402468,"fraction":0.5}}'

- Open hedge
  curl -sX POST "$DJANGO/api/v1/actions/query" \
    -H 'Content-Type: application/json' \
    -d '{"type":"position_hedge","payload":{"ticket":302402468,"volume":0.10}}'

LLM categories (naming)
- Positions: `position_*`
- Account/State: `account_*`, `state_*`
- Market/Scan: `market_*`, `liquidity_map`, `opportunity_*`
- Journal/Behavior: `journal_*`, `whisper_*`

Notes
- Keep adding verbs to the enum in `openapi.actions.yaml` and a matching branch in `ActionsQueryView`.
- You can keep this entire surface to a single operation for GPT.

Trusted Connector Setup
- To remove confirmation popups when the agent calls the Actions Bus, mark the connector as trusted in the schema.
- Add at the root of `openapi.actions.yaml`:
  ```yaml
  x-openai:
    trusted: true
    permissions:
      - domain: django2.zanalytics.app
        always_allow: true
  ```
- Operational guardrails when auto‑allow is enabled:
  - Require `X-Idempotency-Key` for mutating calls.
  - Journal all trade actions (`/api/v1/journal/append`).
  - Optionally scope permissions to specific verbs or restrict in your client runtime.
