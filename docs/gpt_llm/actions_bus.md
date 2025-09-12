# Actions Bus (Slim) – Agent-Facing Verbs

Purpose: expose a compact set of LLM/agent operations via one endpoint to keep the main OpenAPI under the 30‑operation cap.

Base: `https://mcp2.zanalytics.app`

Endpoint: `POST /api/v1/actions/query`

Content‑Type: `application/json`

Body (common):
```
{ "type": string, "payload": object }
```

Current verbs

- `trades_recent`
  - Payload: `{ "limit": number }` (optional; default 200; max 1000)
  - Response: array of TradeItem
    - TradeItem: `{ id, ts_open?, ts_close?, symbol, side?, entry?, exit?, pnl?, rr?, strategy?, session? }`

- `whisper_suggest`
  - Payload: `{ "symbol": string, "user_id": string }`
  - Response:
    ```
    {
      "message": string | null,
      "heuristics": [ { ...serialized_heuristic_whisper... } ],
      "meta": { "user_id": string, "symbol": string }
    }
    ```

Examples

1) Last 100 trades
```
POST /api/v1/actions/query
{ "type": "trades_recent", "payload": { "limit": 100 } }
```

2) Quick behavioral suggestion for XAUUSD
```
POST /api/v1/actions/query
{ "type": "whisper_suggest", "payload": { "symbol": "XAUUSD", "user_id": "local" } }
```

Notes

- The bus is intentionally not included in the main `openapi.yaml` to keep that spec ≤ 30 operations. A separate slim spec `openapi.actions.yaml` is available for LLM manifests.
- Whisper suggestions are best‑effort and rate‑limited server‑side. They prefer a concise one‑liner suitable for dashboards or Discord relays.
- For broader actions (e.g., history ranges, behavior summaries), add verbs here rather than growing the main REST surface.

