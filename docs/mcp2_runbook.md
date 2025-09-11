# MCP2 Service Runbook

The simplified MCP2 service exposes endpoints for trade capture and basic document search. Set `MCP_HOST` to the base URL (default `localhost:8002`).

An OpenAI tools manifest at [`docs/connectors/actions_openai_mcp2.yaml`](connectors/actions_openai_mcp2.yaml) lists the functions exposed by this service:

| Tool               | HTTP route           |
|--------------------|----------------------|
| `search_docs`      | `GET /search_docs`   |
| `fetch_payload`    | `GET /fetch_payload` |
| `log_enriched_trade` | `POST /log_enriched_trade` |
| `get_recent_trades` | `GET /trades/recent` |

## Startup
Build and run the service locally:

```bash
docker build -t mcp2-service -f services/mcp2/Dockerfile .
docker run --rm -p 8002:8002 mcp2-service \
  uvicorn services.mcp2.app:app --host 0.0.0.0 --port 8002
```

## Health
Verify the service is up:

```bash
curl -s $MCP_HOST/health
```

## Trade Logging
Submit a trade payload using the `StrategyPayloadV1` schema:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  --data '{"strategy":"demo","timestamp":"2024-01-01T00:00:00Z","market":{"symbol":"AAPL","timeframe":"1D"},"features":{},"risk":{},"positions":{}}' \
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

## Kafka Integration

Setting the environment variable `MCP2_ENABLE_KAFKA=true` enables an optional Kafka producer.
When enabled, every payload sent to `POST /log_enriched_trade` is also produced to the `mcp2.enriched_trades` topic.
The producer connects to the broker configured by `MCP2_KAFKA_BOOTSTRAP` (default `localhost:9092`).

