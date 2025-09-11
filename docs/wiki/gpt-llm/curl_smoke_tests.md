# MCP2 Curl Smoke Tests

Use these commands to validate that the service is reachable and responding as
expected.

```bash
# Health check
curl -sSf http://localhost:8080/health

# Basic completion request
curl -sSf -X POST http://localhost:8080/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "ping"}'
```
