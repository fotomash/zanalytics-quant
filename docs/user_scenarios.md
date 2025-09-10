# Typical User Scenarios

### a) **Viewing Real-time Market Data**
- Login to your Streamlit dashboard.
- Choose the market or instrument (e.g. EURUSD, GBPUSD, DXY).
- See live tick charts, rolling bars, and indicator overlays.
- Historical data is automatically loaded from Postgres or Parquet (as configured).

### b) **Running Enrichment/Bulk Sync**
- To refresh features or add new data:
    ```bash
    docker exec -it dashboard bash
    python utils/enrich_features.py  # Or your enrichment script
    ```
- These scripts typically fetch new ticks/bars, calculate rolling stats (SMA, RSI, etc), and push back to Postgres or Redis.

### c) **API Data Access**
- Pull ticks:
    ```bash
    curl "$MT5_API_URL/ticks?symbol=GBPUSD&limit=50"
    ```
- Pull bars:
    ```bash
    curl "$MT5_API_URL/bars/EURUSD/M5?limit=200"
    ```
- Pull enriched features via Django API:
    ```bash
    curl "$DJANGO_API_URL/api/v1/enriched/?symbol=USDJPY"
    ```
- Filter ticks or bars by time range using the Django API:
    ```bash
    curl "$DJANGO_API_URL/api/v1/ticks/?symbol=EURUSD&time_after=2024-01-01T00:00:00Z&time_before=2024-01-01T12:00:00Z"
    curl "$DJANGO_API_URL/api/v1/bars/?symbol=EURUSD&timeframe=M5&time_after=2024-01-01T00:00:00Z"
    ```

### d) **Troubleshooting**
- Dashboard blank?
  Check the API/DB container logs, ensure enrichment is running, and verify `.env` secrets.
- MT5 error?
  Make sure Wine is running and your license/user is set in the `.env`.
- Traefik returns 404?
  Traefik 404s typically mean the service is missing router/service labels.
  ```yaml
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.<svc>.rule=Host(`<your-domain>`)
    - "traefik.http.services.<svc>.loadbalancer.server.port=<port>"
  ```
  If Traefik returns 404, add the above labels to the service in your `docker-compose`.
