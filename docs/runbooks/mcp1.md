# MCP1 Runbook

## Environment Variables

- `MCP_API_KEY`: API token required in `Authorization` or `X-API-Key` headers.
- `INTERNAL_API_BASE`: Base URL for forwarding requests to internal services.

## Endpoints

- `GET /health` – liveness probe.
- `POST /api/v1/actions/query` – invoke an enumerated action.
- `POST /exec` – proxy requests to internal APIs.

## Authentication

Include the API key using either header:

```text
Authorization: Bearer $MCP_API_KEY
X-API-Key: $MCP_API_KEY
```

## Smoke Tests

```bash
curl -f http://localhost:8001/health

curl -H "Authorization: Bearer $MCP_API_KEY" \
     -N http://localhost:8001/mcp

curl -X POST http://localhost:8001/api/v1/actions/query \
     -H "Authorization: Bearer $MCP_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"type":"whisper_suggest"}'

curl -X POST http://localhost:8001/exec \
     -H "X-API-Key: $MCP_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"type": "ping", "payload": {}}'
```

## Common Failure Modes

- `401 Unauthorized`: Missing or incorrect API key in headers.
- `422 Unprocessable Entity`: Malformed JSON body or missing required fields.

## Observability

- Prometheus metrics exposed at `GET /metrics` (e.g., `mcp_requests_total`).
- Heartbeat gauge `mcp_up` and timestamp metric `mcp_last_heartbeat_timestamp`.
- Logs stream to standard output; inspect with `docker logs mcp1` or equivalent.
