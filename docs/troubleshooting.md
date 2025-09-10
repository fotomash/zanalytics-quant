# Troubleshooting

## 404 Route Checks
- Use `curl -I http://localhost:8000/<route>` to confirm the service responds and to inspect headers.
- Verify the target container is running: `docker compose ps`.
- For Traefik routed services, confirm `Host` and `PathPrefix` labels match the request.

## Heartbeat Timeout Fixes
- Timeouts usually indicate a stalled worker or lost connection to Redis or Kafka.
- Inspect service logs for heartbeat warnings and network errors.
- Restart the affected service and ensure the backend is reachable.
- Increase the heartbeat interval (`--heartbeat-interval` or env vars) if the network is slow.

## Traefik 502 Log Paths
- `docker compose logs traefik` shows gateway errors and upstream details.
- File-based logs default to `/var/log/traefik/traefik.log` and `/var/log/traefik/access.log` inside the Traefik container.
- Combine these logs with backend service logs to locate the failing upstream.

## Common Compose Failures
- **Port conflicts** – ensure required ports are free (`lsof -i :PORT`).
- **Missing environment variables** – verify `.env` files and exported vars.
- **Out-of-date images** – run `docker compose pull` to update tags.
- **Volume permission errors** – check host directory ownership.
- **Compose plugin/version mismatch** – confirm `docker compose version` ≥ 2.
