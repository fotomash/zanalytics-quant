# MCP2 Service Runbook

The simplified MCP2 service exposes endpoints for trade capture and basic document search. Set `MCP_HOST` to the base URL (default `localhost:8002`).

An OpenAI tools manifest at [`docs/connectors/actions_openai_mcp2.yaml`](connectors/actions_openai_mcp2.yaml) lists the functions exposed by this service:

| Tool               | HTTP route           |
|--------------------|----------------------|
| `search_docs`      | `GET /search_docs`   |
| `fetch_payload`    | `GET /fetch_payload` |
| `log_enriched_trade` | `POST /log_enriched_trade` |
| `get_recent_trades` | `GET /trades/recent` |
The accompanying `mcp2-pg` container loads [services/mcp2/init.sql](../services/mcp2/init.sql) on startup to create the `docs` table used for searches.

## Authentication
Set `MCP2_API_KEY` to enable request authentication. When set, clients must provide the key in either an `X-API-Key` header or an `Authorization: Bearer <key>` header.

```bash
curl -H "X-API-Key: $MCP2_API_KEY" $MCP_HOST/health
```

## Startup
Build and run the service locally:

```bash
docker build -t mcp2-service -f services/mcp2/Dockerfile .
docker run --rm -p 8002:8002 mcp2-service \
  uvicorn services.mcp2.app:app --host 0.0.0.0 --port 8002
```

## Auth
Set a secret in `MCP2_API_KEY` and include it with every request using the `X-API-Key` header:

```bash
curl -H "X-API-Key: $MCP2_API_KEY" "$MCP_HOST/search_docs?query=alpha"
```

## Health
Verify the service is up:

```bash
curl -s -H "X-API-Key: $MCP2_API_KEY" $MCP_HOST/health
```

## Metrics
Prometheus metrics are exposed at `/metrics`:

```bash
curl -s $MCP_HOST/metrics | head
```

## Trade Logging
Submit a trade payload using the `StrategyPayloadV1` schema:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -H "X-API-Key: $MCP2_API_KEY" \
  --data '{"strategy":"demo","timestamp":"2024-01-01T00:00:00Z","market":{"symbol":"AAPL","timeframe":"1D"},"features":{},"risk":{},"positions":{}}' \
  $MCP_HOST/log_enriched_trade
```

## Doc Search
Query indexed documentation:
```bash

curl -s -H "X-API-Key: $MCP2_API_KEY" "$MCP_HOST/search_docs?query=alpha"
```

## Payload Retrieval
Fetch stored payloads:

```bash
# by id
curl -s -H "X-API-Key: $MCP2_API_KEY" "$MCP_HOST/fetch_payload?id=<id>"

# recent trades
curl -s -H "X-API-Key: $MCP2_API_KEY" "$MCP_HOST/trades/recent?limit=5"
```

## Kafka Integration

Setting the environment variable `MCP2_ENABLE_KAFKA=true` enables an optional Kafka producer.
When enabled, every payload sent to `POST /log_enriched_trade` is also produced to the `mcp2.enriched_trades` topic.
The producer connects to the broker configured by `MCP2_KAFKA_BOOTSTRAP` (default `localhost:9092`).


## Kafka
If `KAFKA_BROKERS` is configured the service also publishes payloads to the `enriched-analysis-payloads` topic. Without brokers the producer operates as a no-op.

```bash
export KAFKA_BROKERS=localhost:9092
# logs still succeed even if Kafka is unreachable
```

## Redis Streams
Enriched signals are mirrored into Redis Streams. Inspect them via `redis-cli`:

```bash
redis-cli XRANGE ml:signals - + LIMIT 5
redis-cli XRANGE ml:risk - + LIMIT 5
```
