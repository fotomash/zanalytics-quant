# Info Site

The public info site mirrors content from this repository's `docs/` folder.

## Content Source

- The container mounts the `docs/` directory as read-only.
- `info-site.md` serves as the landing page.
- Any additional Markdown under `docs/` becomes a navigable page.
- During the Docker build, `services/info` copies `docs/wiki` and
  `dashboards/info` into the image so the wiki and dashboard are baked in
  by default.

## Deployment

- A lightweight Streamlit app renders the Markdown files.
- You can also generate a static site with tools like MkDocs.
- The app listens on `WIKI_DASHBOARD_PORT` (default `8503`). Traefik routes
  `info.zanalytics.app` to this container on that port.
- Example `docker compose` snippet:
  ```yaml
  volumes:
    - ./docs:/app/docs:ro
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.info.rule=Host(`info.zanalytics.app`)"
    - "traefik.http.services.info.loadbalancer.server.port=8503"
  ```
  Traefik routes HTTPS traffic to the Streamlit container on port `8503`.
- For local testing:
  ```bash
  docker compose build info && docker compose up -d info
  ```

## Auto-sync

A GitHub Action keeps the deployed docs in sync with the repository:

```yaml
name: sync-info-site
on:
  push:
    paths:
      - "docs/**"
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Sync docs via rsync
        run: |
          rsync -avz docs/ ${{ secrets.INFO_HOST }}:/opt/zanalytics/docs
```

Pushing changes to `docs/` updates the live site within seconds.

## Post-deploy Copy

Some environments rebuild the Streamlit image without the latest docs. A CI job or
post-deploy script can refresh the running container by copying the repository's
`docs/` directory into it whenever documentation changes.

```yaml
name: copy-docs-to-container
on:
  push:
    paths:
      - "docs/**"
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Rebuild container and copy docs
        run: |
          docker compose up -d --build info
          docker cp docs/. $(docker compose ps -q info):/app/docs
```

For Compose-based deployments, the `develop.watch` feature can automatically
rebuild the container when files in `docs/` change:

```yaml
services:
  info:
    build: .
    volumes:
      - ./docs:/app/docs
    develop:
      watch:
        - path: ./docs
          action: rebuild
```

Either approach ensures the running Streamlit container serves the most recent
documentation.
