# MCP2 Service Runbook

## Purpose
MCP2 exposes strategy tooling endpoints for logging trades and searching documentation.

## Environment Variables
- `REDIS_URL` – Redis connection string (defaults to `redis://localhost:6379/0`)
- `DATABASE_URL` – Postgres connection string (defaults to `postgresql://postgres:postgres@localhost:5432/postgres`)
- `MCP_HOST` – base URL for the MCP2 service (defaults to `localhost:8002`)

## Health
Check service availability:

```bash
curl -s $MCP_HOST/health
```

## Trade Logging
Log a trade payload:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"strategy":"demo","symbol":"AAPL","timeframe":"1D","date":"2024-01-01T00:00:00Z"}' \
  $MCP_HOST/log_enriched_trade
```

## Doc Search
Search indexed documents:

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

## Notes
Embeddings are stubbed and search is simple keyword matching. pgvector integration will arrive in PR-4.
