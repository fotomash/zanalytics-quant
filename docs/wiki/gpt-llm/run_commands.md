# MCP2 Run Commands

Use the following commands to build and run the MCP2 service locally.

```bash
# Build the container
docker build -t mcp2-service -f services/mcp2/Dockerfile .

# Start the server
docker run --rm -p 8002:8002 mcp2-service \
  uvicorn services.mcp2.app:app --host 0.0.0.0 --port 8002
```

The environment variable `MCP2_CACHE_TTL` controls cache expiry. Set it to match
production defaults during local testing.
