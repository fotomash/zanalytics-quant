# Authentication

All HTTP requests to the MCP server must include the `X-API-Key` header, except for the `/mcp` heartbeat endpoint.

## Example request

Use a development key such as `dev-key-123` during local testing:

```bash
curl -s -H "X-API-Key: dev-key-123" -X POST \
  http://localhost:8080/api/v1/actions/query \
  -d '{"type": "session_boot"}'
```

## Rotating the key

The server reads the key from the `MCP_API_KEY` environment variable. To rotate it:

1. Set a new value in your environment or `.env` file: `MCP_API_KEY=new-key`.
2. Restart the service so it picks up the new key, e.g. `docker compose up --build mcp`.
3. Update clients to send the new `X-API-Key` header.


Last validated: 2025-09-10 15:07:51Z
