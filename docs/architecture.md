# Architecture

## Network Routing

The diagram below shows external traffic flowing from the host through Traefik to internal services and their data stores. It also highlights the `/exec` call from the MCP service into Django.

```mermaid
graph LR
    host[Host] --> traefik[Traefik]
    traefik --> django[Django:8000]
    traefik --> mcp[MCP:8001]
    traefik --> dashboard[Dashboard:8501]
    traefik --> grafana[Grafana:3000]
    traefik --> mt5[MT5 Bridge:5001]
    mcp -->|"/exec"| django
    django --> postgres[(PostgreSQL)]
    django --> redis[(Redis)]
    mt5 --> redis
```

