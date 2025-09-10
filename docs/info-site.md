# Info Site

The public info site mirrors content from this repository's `docs/` folder.

## Content Source

- The container mounts the `docs/` directory as read-only.
- `info-site.md` serves as the landing page.
- Any additional Markdown under `docs/` becomes a navigable page.

## Deployment

- A lightweight Streamlit app renders the Markdown files.
- You can also generate a static site with tools like MkDocs.
- Example `docker-compose` snippet:
  ```yaml
  volumes:
    - ./docs:/app/docs:ro
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.info.rule=Host(`info.example.com`)"
    - "traefik.http.services.info.loadbalancer.server.port=8501"
  ```
  Traefik routes HTTPS traffic to the Streamlit container on port `8501`.

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
