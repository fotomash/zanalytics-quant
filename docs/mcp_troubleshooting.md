# MCP Troubleshooting

This guide focuses on common issues when running the MCP server behind Traefik and Docker.
For general problems across the stack, see [troubleshooting.md](troubleshooting.md).

## Required Traefik Labels
Expose the MCP server through Traefik with labels similar to:

```yaml
docker compose:
  services:
    mcp_server:
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.mcp.rule=Host(`mcp1.example.com`)"
        - "traefik.http.routers.mcp.entrypoints=websecure"
        - "traefik.http.services.mcp.loadbalancer.server.port=8001"
```

Missing or mismatched labels typically surface as:
- `404 router mcp@docker not found`
- `503 service unavailable` if the backend is down

Restart Traefik after updating labels:

```bash
docker compose restart traefik
```

## macOS Keychain Unlock
Docker or `git` prompts may hang if the login keychain is locked. Unlock it and rerun the command:

```bash
security unlock-keychain login.keychain-db
```

Add `-p "$KEYCHAIN_PASSWORD"` to supply the password non-interactively.

## Ghost Container Cleanup and Rebuild
Leftover containers can still bind to MCP ports and block redeploys.

```bash
# show stragglers
docker ps -a | grep mcp

# stop the stack and remove volumes
docker compose down -v

# remove any orphaned containers
docker container prune -f

# rebuild and relaunch
docker compose up --build -d mcp_server
```

## Quick Log Commands
Inspect logs to diagnose routing and service errors:

```bash
docker compose logs mcp_server
```
Common messages include `KeyError: 'MCP_API_KEY'` or `Address already in use`.

```bash
docker compose logs traefik
```
Look for entries like `router mcp@docker not found` or TLS certificate errors.

These logs usually pinpoint whether the issue resides in the MCP container or the Traefik gateway.
