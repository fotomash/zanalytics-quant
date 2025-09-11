# Redis Cache Architecture

## Purpose

The caching service provides a low‑latency, in‑memory layer used by the platform to avoid hitting Postgres and Django for every dashboard refresh.  Market data, session state and pre‑computed analytics are stored in Redis so that widgets can render instantly and background services can exchange messages without blocking on the database.

## Key Data Structures and TTL Strategy

- **Strings** – single quotes, positions and feature flags.  Short‑lived values are written with `SETEX` and expire automatically.
- **Hashes** – grouped statistics such as open orders or account metrics.  A default TTL of **60 seconds** can be overridden with `CACHE_TTL`.
- **Sorted Sets** – time‑series snapshots where scores are timestamps.  Older entries are trimmed by the producer while recent elements are kept for quick range queries.
- **Pub/Sub channels** – transient events (tick updates, notifications) that do not require persistence.

The TTL strategy keeps the working set small: ticks typically expire in a few seconds, dashboard aggregations in a minute, and long‑running reference data is either refreshed manually or stored without an expiry.

## Dashboard Consumption

The Streamlit dashboard reads from Redis using the `REDIS_URL` environment variable.  Widgets query hashes for the latest account state, fetch strings for quick counters and subscribe to channels for live updates.  When data is not in the cache the dashboard gracefully falls back to the Django API.

## Deployment

### Environment Variables

Add the following to your `.env` file:

```env
REDIS_URL=redis://redis:6379/0
CACHE_TTL=60  # seconds for generic cache entries
```

### docker‑compose

The `redis` service is already defined in `docker-compose.yml`.  Ensure dashboard and other consumers reference it:

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
  dashboard:
    environment:
      - REDIS_URL=${REDIS_URL:-redis://redis:6379/0}
    depends_on:
      redis:
        condition: service_healthy
```

Start the cache and dashboard with:

```bash
docker-compose up -d redis dashboard
```

These settings allow any component with `REDIS_URL` configured to leverage the shared cache without additional setup.
