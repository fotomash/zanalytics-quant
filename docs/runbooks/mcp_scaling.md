# MCP Scaling Runbook

Guidelines for scaling Multiple Control Plane (MCP) services and isolating Redis workloads.

## When to Split Redis
- **High memory or CPU**: separate Redis when `INFO memory` shows usage consistently above 70% or latency spikes.
- **Service interference**: isolate heavy Celery queues, journaling streams, and MCP caches so one cannot evict another's keys.
- **Security boundaries**: use distinct instances when different teams manage data or keys must remain segregated.

Recommended layout:

| Service | Redis DB/Instance |
|---------|------------------|
| MCP cache | `redis://mcp-redis:6379/0` |
| Celery broker | `redis://celery-redis:6379/0` |
| Journal streams | `redis://journal-redis:6379/0` |

## Deploying Multiple MCP Services
1. Clone the existing service directory and adjust ports and prefixes:
   ```bash
   cp -r services/mcp2 services/mcp3
   export REDIS_URL=redis://mcp3-redis:6379/0
   uvicorn services.mcp3.main:app --port 8003
   ```
2. In `docker-compose.yml`, add a new service block and unique `DNS_PREFIX`.
3. Update Prometheus or other monitors to scrape the new service.

## OpenAI MCP Connector Example
Configure each MCP service with its own connector entry and API key:

```yaml
# .well-known/ai-plugin.json or actions manifest
servers:
  - url: https://mcp2.zanalytics.app/
    api_key: ${MCP2_API_KEY}
  - url: https://mcp3.zanalytics.app/
    api_key: ${MCP3_API_KEY}
```

## Redis Key Isolation
Prefix keys per service to avoid collisions:

```python
# services/mcp2/storage/redis_client.py
PREFIX = "mcp2:"
redis.set(f"{PREFIX}payload:{id}", data)
```

Celery tasks might use `celery:` and journal writers `journal:`. Keep prefixes consistent across deployments.

## Monitoring Redis Saturation
- `redis-cli info memory` – check `used_memory_human`, `evicted_keys`, and `connected_clients`.
- Track command rate: `redis-cli info stats | grep instantaneous_ops_per_sec`.
- Export metrics via `redis_exporter` and alert when `used_memory_ratio` exceeds 0.8.
- Add application logs when `BlockingError` or timeouts occur to correlate with Redis pressure.

Early alerts on these signals let you provision new Redis instances or tune eviction policies before outage.
