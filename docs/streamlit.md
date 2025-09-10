# Streamlit Info Site

The repository uses a minimal Streamlit app to present Markdown files from `docs/` as a public information site.

## Default Port

- The app listens on port `8501` inside the container.

## Traefik Routing

A typical `docker compose` setup routes HTTPS traffic through Traefik to the Streamlit container:

```yaml
volumes:
  - ./docs:/app/docs:ro
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.info.rule=Host(`info.example.com`)"
  - "traefik.http.services.info.loadbalancer.server.port=8501"
```

## Docs Mount

- The container mounts the repository's `docs/` directory read-only.
- Each Markdown file becomes a page on the public info site.

This setup keeps the site in sync with the repository; pushing changes to `docs/` updates the live content.

For the dedicated info container and deployment details, see [info-site.md](info-site.md).
