# API Security

## Setting and rotating the API key

- Set the API key value in an environment variable named `MCP2_API_KEY`. Avoid hard-coding it in source code or configuration files.
- Rotate the key on a regular schedule and update `MCP2_API_KEY` accordingly.
- For local development you can use a test value such as `dev-key-123`.

## Public vs. protected endpoints

- `/mcp` and `/health` are public heartbeat endpoints and require no authentication.
- Other routes, like `POST /api/v1/actions/query` or `/exec/...`, must include both the `Authorization: Bearer <key>` and `X-API-Key: <key>` headers.

## Curl example

```bash
curl -sX POST http://localhost:8080/api/v1/actions/query \
  -H "Authorization: Bearer dev-key-123" \
  -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"type":"session_boot","payload":{"user_id":"demo"}}'
# Omitting the headers returns 401 Unauthorized
curl -sX POST http://localhost:8080/api/v1/actions/query \
  -H "Content-Type: application/json" \
  -d '{"type":"session_boot","payload":{"user_id":"demo"}}'
```

The `Content-Type: application/json` header is required when sending JSON bodies.

See [auth](auth.md) for additional authentication examples and key rotation steps.

## OpenAI connector setup

In the OpenAI connector, configure:

- **Authentication → Custom**
- **Header Name:** `Authorization`
- **Value:** `Bearer dev-key-123`
- **Header Name:** `X-API-Key`
- **Value:** `dev-key-123`

## Whisperer sessions

Upon successful authentication, the Whisperer component can initiate sessions safely.

