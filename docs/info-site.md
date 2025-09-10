# Static Info Site Deployment

## Mounting

- Mount the repository's `docs` directory into the container:
  ```yaml
  volumes:
    - ./docs:/app/docs:ro
  ```
- The container serves `docs/info-site.md` as the root page.

## Streamlit App Behavior

- A lightweight Streamlit app renders markdown from the mounted docs folder.
- Visiting `/` loads `info-site.md` by default.
- Additional markdown files under `docs/` become navigable pages.

## Traefik Routing

- Enable routing with labels:
  ```yaml
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.info.rule=Host(`info.example.com`)"
    - "traefik.http.services.info.loadbalancer.server.port=8501"
  ```
- Traefik forwards HTTPS traffic to the Streamlit container on port `8501`.

## Deployment YAML

Example Kubernetes deployment:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: info-site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: info-site
  template:
    metadata:
      labels:
        app: info-site
    spec:
      containers:
        - name: info-site
          image: ghcr.io/zananalytics/info-site:latest
          ports:
            - containerPort: 8501
          volumeMounts:
            - name: docs
              mountPath: /app/docs
      volumes:
        - name: docs
          hostPath:
            path: /opt/zanalytics/docs
            type: Directory
```

## Optional GitHub Action for `rsync`

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
