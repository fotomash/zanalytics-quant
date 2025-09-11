# MCP2 Run Commands

Use the following commands to build and run the MCP2 service locally.

```bash
# Build the container
docker build -t mcp2-service -f Dockerfile.mcp2 .

# Run migrations and start the server
docker run --rm -p 8080:8080 mcp2-service python manage.py migrate
docker run --rm -p 8080:8080 mcp2-service python manage.py runserver 0.0.0.0:8080
```

The environment variable `MCP2_CACHE_TTL` controls cache expiry. Set it to match
production defaults during local testing.
