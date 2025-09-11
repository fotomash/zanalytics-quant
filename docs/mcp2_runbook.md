# MCP2 Service Runbook

The simplified MCP2 service exposes endpoints for trade capture and basic document search. Set `MCP_HOST` to the base URL (default `localhost:8002`).

An OpenAI tools manifest at [`docs/connectors/actions_openai_mcp2.yaml`](connectors/actions_openai_mcp2.yaml) lists the functions exposed by this service:

| Tool               | HTTP route           |
|--------------------|----------------------|
| `search_docs`      | `GET /search_docs`   |
| `fetch_payload`    | `GET /fetch_payload` |
| `log_enriched_trade` | `POST /log_enriched_trade` |
| `get_recent_trades` | `GET /trades/recent` |

## Health
Verify the service is up:

```bash
curl -s $MCP_HOST/health
```

## Trade Logging
Submit a trade payload:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"strategy":"demo","symbol":"AAPL","timeframe":"1D","date":"2024-01-01T00:00:00Z"}' \
  $MCP_HOST/log_enriched_trade
```

## Doc Search
Query indexed documentation:

```bash
curl -s "$MCP_HOST/search_docs?query=alpha"
```

## Payload Retrieval
Fetch stored payloads:

```bash
# by id
curl -s "$MCP_HOST/fetch_payload?id=<id>"

# recent trades
curl -s "$MCP_HOST/trades/recent?limit=5"
```
