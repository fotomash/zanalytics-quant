# MCP1 Runbook

## Environment Variables

- `MCP_API_KEY`: API token required in `Authorization` or `X-API-Key` headers.
- `INTERNAL_API_BASE`: Base URL for forwarding requests to internal services.

## Smoke Tests

```bash
curl -f http://localhost:8001/health

curl -H "Authorization: Bearer $MCP_API_KEY" \
     -N http://localhost:8001/mcp

curl -X POST http://localhost:8001/exec \
     -H "Authorization: Bearer $MCP_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"type": "ping", "payload": {}}'
```

## Common Failure Modes

- `401 Unauthorized`: Missing or incorrect API key in headers.
- `422 Unprocessable Entity`: Malformed JSON body or missing required fields.
