# API Security

## Setting and rotating `X-API-Key`

- Set the `X-API-Key` value in an environment variable named `MCP_API_KEY`. Avoid hard-coding it in source code or configuration files.
- Rotate the key on a regular schedule and update `MCP_API_KEY` accordingly.
- For local development you can use a test value such as `dev-key-123`.

## Public vs. protected endpoints

- `/mcp` is a public heartbeat endpoint and requires no authentication.
- Other routes, like `/api/v1/actions/read` or `/exec/...`, must include the `X-API-Key` header.

## Curl example

```bash
curl -s -H "X-API-Key: dev-key-123" http://localhost:8080/api/v1/actions/read
# Omitting the header returns 401 Unauthorized
curl -s http://localhost:8080/api/v1/actions/read
```

See [auth](auth.md) for additional authentication examples and key rotation steps.

## OpenAI connector setup

In the OpenAI connector, configure:

- **Authentication → Custom**
- **Header Name:** `X-API-Key`
- **Value:** `dev-key-123`

## Whisperer sessions

Upon successful authentication, the Whisperer component can initiate sessions safely.

