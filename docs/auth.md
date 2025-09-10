# Authentication

This guide explains how to authenticate requests to the MCP server. For more background see [API Security](api-security.md).

## Example requests

The `X-API-Key` header must be supplied for most endpoints. Use a development key such as `dev-key-123` during local testing.

```bash
# Public heartbeat
curl -s http://localhost:8080/mcp

# Authenticated action
curl -s -H "X-API-Key: dev-key-123" \
  http://localhost:8080/api/v1/actions/read
```

## Endpoint rules

- `/mcp` is unauthenticated and acts as a heartbeat.
- `/api/v1/actions/...` and similar routes require the `X-API-Key` header.

## Rotating the key

1. Set a new value for `MCP_API_KEY` in your `.env` file.
2. Run `docker compose up --build mcp` to rebuild the service with the updated key.
3. Update the key in the connector UI so clients send the new header.

## Why this matters

Rotating the key prevents "Error talking to connector" pop-ups while keeping the heartbeat endpoint public.

