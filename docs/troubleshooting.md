# Troubleshooting

For MCP-specific routing and container issues, see [mcp_troubleshooting.md](mcp_troubleshooting.md).

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

## Traefik Routing Labels
- Ensure labels like `traefik.enable` and `traefik.http.routers.*.rule` match the request in [`docker-compose.yml`](../docker-compose.yml).
- Adjust `Host`/`PathPrefix` rules for each service and reload with `docker compose restart traefik`.

## macOS Keychain Unlock
- Unlock the macOS keychain if Docker or `git` prompts stall:
  ```bash
  security unlock-keychain login.keychain-db
  ```
- Re-run the original command after unlocking.

## Ghost Container Cleanup
- List stragglers: `docker ps -a`.
- Remove stale containers and volumes:
  ```bash
  docker compose down -v
  docker container prune -f
  ```
- Rebuild the stack with `docker compose up --build`.

## Whisperer Approval Flag
- Cached actions may ignore `approve: true`.
- Include `force: true` or delete/re-add the connector in the OpenAI builder.
- See [WHISPERER.md](WHISPERER.md) for payload examples.

## Stale MT5 Feeds
- Check the [mt5_gateway](../mt5_gateway/README.md) logs: `docker compose logs mt5`.
- Restart the feed: `docker compose restart mt5`.
- Validate ticks with `curl "$MT5_API_URL/ticks?symbol=EURUSD&limit=1"`.

## API Key Header Usage
- Protected endpoints require `X-API-Key` headers.
- Example:
  ```bash
  curl -H "X-API-Key: $MCP_API_KEY" http://localhost:8001/api/...
  ```
- See [api-security.md](api-security.md) for rotation and storage details.
