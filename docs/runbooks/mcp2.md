# MCP2 Service Runbook

## Purpose
MCP2 exposes strategy tooling endpoints for enriched trades and document search.

## Environment Variables
- `REDIS_URL` – Redis connection string (defaults to `redis://localhost:6379/0`)
- `DATABASE_URL` – Postgres connection string (defaults to `postgresql://postgres:postgres@localhost:5432/postgres`)

## Endpoints
- `GET /health` – basic liveness check
- `POST /log_enriched_trade` – store a `StrategyPayload` in Redis
- `GET /search_docs` – keyword search across docs
- `GET /fetch_payload` – retrieve a logged payload by id
- `GET /trades/recent` – return recent payloads

## Smoke Tests
```
# health
curl -s localhost:8002/health

# log then fetch
echo '{"strategy":"demo","symbol":"AAPL","timeframe":"1D","date":"2024-01-01T00:00:00Z"}' \
  | curl -s -X POST -H 'Content-Type: application/json' --data @- localhost:8002/log_enriched_trade
```

## Notes
Embeddings are stubbed and search is simple keyword matching. pgvector integration will arrive in PR-4.
