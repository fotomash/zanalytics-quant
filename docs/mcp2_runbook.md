# MCP2 Runbook

This guide covers day-to-day operations for the MCP2 service. Set the `MCP_HOST` environment variable to the desired MCP domain before running the commands below.

```bash
export MCP_HOST=mcp2.zanalytics.app
```

## Startup

Build images and start the core services:

```bash
docker compose build mcp django postgres redis
docker compose up -d mcp django postgres redis
```

Run the MCP2 database migration:

```bash
docker compose exec postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f db/migrations/mcp2.sql
```

## Testing Endpoints

Verify the service root and the `/exec` endpoint:

```bash
# SSE heartbeat
curl -k https://$MCP_HOST/mcp | head -3

# Session boot
curl -k -H "Authorization: Bearer $MCP2_API_KEY" -H "X-API-Key: $MCP2_API_KEY" \
  -X POST https://$MCP_HOST/exec \
curl -k https://mcp2.zanalytics.app/mcp | head -3

# Session boot
curl -k -H "Authorization: Bearer $MCP2_API_KEY" -H "X-API-Key: $MCP2_API_KEY" \
  -X POST https://mcp2.zanalytics.app/exec \
  -d '{"type":"session_boot","approve":true}'
```

## Cache and Database Management

Flush Redis and rebuild caches:

```bash
docker compose exec redis redis-cli FLUSHALL
```

Reset Postgres (destructive):

```bash
docker compose down postgres
rm -rf docker/volumes/postgres
docker compose up -d postgres
# rerun migrations
```

## Migration Steps

1. Apply the SQL migration as shown above.
2. Restart services to pick up schema changes:

```bash
docker compose up -d --force-recreate mcp django
```

