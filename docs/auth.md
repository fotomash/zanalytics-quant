# Authentication

All HTTP requests to the MCP server must include the `Authorization: Bearer <key>` and `X-API-Key: <key>` headers, except for the `/mcp` and `/health` heartbeat endpoints.

## Example request

Use a development key such as `dev-key-123` during local testing:

```bash
curl -sX POST http://localhost:8080/api/v1/actions/query \
  -H "Authorization: Bearer dev-key-123" \
  -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"type":"session_boot","payload":{}}'
```

Minimal JSON body:

```json
{ "type": "session_boot", "payload": {} }
```

```bash
curl -sX POST "http://localhost:8080/api/v1/actions/query" \
  -H "Authorization: Bearer dev-key-123" \
  -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"type":"session_boot","payload":{"user_id":"demo"}}'
```

The `Content-Type: application/json` header is required when sending JSON to the Actions Bus.

## Rotating the key

The server reads the key from the `MCP_API_KEY` environment variable. To rotate it:

1. Set a new value in your environment or `.env` file: `MCP_API_KEY=new-key`.
2. Restart the service so it picks up the new key, e.g. `docker compose up --build mcp`.
3. Update clients to send the new `Authorization` and `X-API-Key` headers.


Last validated: 2025-09-10 15:07:51Z
