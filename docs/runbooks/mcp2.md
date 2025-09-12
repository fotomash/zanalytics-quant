# MCP2 Service Runbook

## Startup

Run the service locally with:

```bash
uvicorn services.mcp2.main:app --host 0.0.0.0 --port 8002
```

## Curl Tests

```bash
# document search
curl -H "X-API-Key: $MCP2_API_KEY" \
     "http://localhost:8002/mcp/tools/search?query=alpha"

# fetch stored payload
curl -H "X-API-Key: $MCP2_API_KEY" \
     "http://localhost:8002/mcp/tools/fetch?id=<uuid>"
```

## Storage

- **Redis** stores serialized trade payloads and a list of trade IDs.
- **Postgres** backs the document search endpoint via the `docs` table.

## Scaling and Redis Separation

For guidance on splitting Redis workloads and deploying additional MCP services, see the [MCP Scaling Runbook](mcp_scaling.md).
