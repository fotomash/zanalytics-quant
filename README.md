# Zanalytics Quant Platform

Trader‑first analytics, risk, and execution — backed by MT5, Django, Redis, Postgres, and Streamlit. Now with LLM‑native Actions and safe position control (partials, scaling, hedging).

For deeper architecture insights and API details, visit the [docs README](docs/README.md), the central hub for extended documentation. Redis cache design and deployment steps live in [redis_architecture/README.md](redis_architecture/README.md).

## Table of Contents
- [What's Inside](#whats-inside)
- [Architecture](#architecture)
- [System Overview](#system-overview)
- [pulse-api](#pulse-api)
- [tick-to-bar](#tick-to-bar)
- [Quick Start: MCP2 Metrics & Streams](#quick-start-mcp2-metrics--streams)
- [pulse-api](#pulse-api)
- [ticktobar](#ticktobar)
- [Getting Started – Quick Launch](#getting-started-quick-launch)
- [Environment Variables](#environment-variables)
- [MT5 service vs. Django API](#mt5-service-vs-django-api)
- [How It Works (Practical Flow)](#how-it-works-practical-flow)
- [Data Integrity and Deduplication](#data-integrity-and-deduplication)
- [MT5 Bridge & Orders (Execution)](#mt5-bridge-orders-execution)
- [Actions Bus for GPT (≤30 operations)](#actions-bus-for-gpt-30-operations)
- [Dashboards & Diagnostics](#dashboards-diagnostics)
- [Journaling (ZBAR)](#journaling-zbar)
- [Typical User Scenarios](#typical-user-scenarios)
- [Data Enrichment & Customization](#data-enrichment-customization)
- [Confidence Trace Matrix](#confidence-trace-matrix)
- [Example .env Configuration](#example-env-configuration)
- [Security & Access Control](#security-access-control)
- [API Health Check and Query Examples](#api-health-check-and-query-examples)
- [Contributing](#contributing)
- [Running Tests](#running-tests)
- [Known Issues & Best Practices](#known-issues-best-practices)
- [Future Directions & Next Steps](#future-directions-next-steps)

- [License](#license)
- [Advanced Usage](#advanced-usage)
- [Kafka Replay Consumer](#kafka-replay-consumer)

- [Full API Documentation](#full-api-documentation)
- [FAQ](#faq)
- [Troubleshooting Gold Mine](#troubleshooting-gold-mine)
- [MCP2 Runbook](#mcp2-runbook)
- [Pulse Dashboard Prototype](#pulse-dashboard-prototype)
- [Further Reading](#further-reading)

## What's Inside
- `backend/mt5`: Flask bridge to MetaTrader5 (send orders, partial close, hedge, scale)
- `backend/django`: REST API, Actions Bus router, positions aliases, journal
- [`dashboard/`](dashboard/README.md): Streamlit UI (Pulse, Whisperer, diagnostics)
- [`dashboards/`](dashboards/README.md): standalone examples and templates
- `openapi.actions.yaml`: the single schema to upload to Custom GPT
- `docs/`: deep dives (Actions Bus, Positions & Orders, Journaling schema)

## Architecture
```mermaid
graph LR
  Trader/LLM -->|Action| ActionsBus[/POST /api/v1/actions/query/]
  ActionsBus -->|verb route| Django[Django API]
  Django -->|orders proxy| MT5[MT5 Bridge]
  Django --> Postgres[(Postgres)]
  Django --> Redis[(Redis)]
  Streamlit[Dashboards] --> Django
  MT5 -->|positions/history| Django
```

For detailed network flows, MCP2 responsibilities, and storage topology, see [docs/architecture.md](docs/architecture.md).

## System Overview

The Zanalytics Quant platform is architected to meet the rigorous demands of professional quantitative research and trading. Each component has a distinct role designed to maximize security, modularity, and performance:

- **MT5** serves as the primary market data source and trading engine, running inside a Docker container with Wine to ensure consistent cross-platform operation. It exposes a REST API for data retrieval and order management, isolating the trading environment from other system components for security and stability.

- **Django API** acts as the orchestrator and backend service layer. It manages user authentication, enforces access controls, and provides RESTful endpoints for data retrieval and command execution. The API encapsulates business logic and database interactions, ensuring secure and auditable operations.

- **Redis** is leveraged as a high-performance in-memory cache and message bus. It stores real-time tick and bar data, event streams, and intermediate enrichment results to enable low-latency analytics and dashboard updates. Redis caching reduces load on the main database and supports real-time responsiveness.

- **Postgres** is the authoritative data store for all historical and enriched market data, including ticks, bars, positions, and computed features. It provides transactional integrity and supports complex queries required for backtesting and research.

- **Enrichment Scripts** located in the `utils/` directory perform data transformation, feature engineering, and batch ETL processes. They convert raw market data into actionable alpha features, rolling statistics, and signals, which are then persisted back to Postgres and cached in Redis.

- **Streamlit Dashboard** offers a user-friendly, interactive frontend for visualization and analysis. It consumes data from the Django API and Redis cache, presenting live and historical market insights with customizable charts and controls.

This modular design facilitates secure separation of concerns, easy extensibility for new features or data sources, and robust performance for professional quant workflows.

## pulse-api

**Purpose**: Exposes the Pulse runtime over HTTP so other services can request confluence scores, perform risk checks, and append journal entries.

**Build & Run**

```bash
docker compose -f docker-compose.pulse.yml up --build pulse-api
```

**Required Environment Variables**

- `PULSE_CONFIG` – path to the Pulse YAML configuration.
- `PULSE_API_KEY` – API key expected in the `X-API-Key` request header.

See [docker-compose.pulse.yml](docker-compose.pulse.yml) for a full example stack.

## tick-to-bar

**Purpose**: Aggregates raw tick streams into OHLCV bars and publishes them to Redis or downstream consumers.

**Build & Run**

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build tick-to-bar
```

**Required Environment Variables**

- `REDIS_HOST` – Redis hostname.
- `REDIS_PORT` – Redis port.
- `SYMBOLS` – comma-separated instruments to process.
- `KAFKA_BOOTSTRAP_SERVERS` – Kafka broker addresses.
- `KAFKA_TICKS_TOPIC` – source topic for tick data.
- `KAFKA_GROUP_ID` – consumer group identifier.

See [docker-compose.override.yml](docker-compose.override.yml) (extends [docker-compose.yml](docker-compose.yml)) for configuration details.

## Quick Start: MCP2 Metrics & Streams

```bash
export MCP_HOST=http://localhost:8002
export MCP2_API_KEY=your-dev-key

# Authenticated doc search
curl -H "X-API-Key: $MCP2_API_KEY" "$MCP_HOST/search_docs?query=alpha"

# Prometheus metrics
curl "$MCP_HOST/metrics" | head

# Optional Kafka topic (no-op if brokers unset)
export KAFKA_BROKERS=localhost:9092
# payloads go to enriched-analysis-payloads

# Inspect Redis Streams
redis-cli XRANGE ml:signals:v1 - + LIMIT 5
redis-cli XRANGE ml:risk:v1 - + LIMIT 5
```

## pulse-api

FastAPI shim that exposes PulseKernel scoring, risk, and journaling features to other services.

**Build and run**

```bash
docker compose -f docker-compose.pulse.yml build pulse-api
docker compose -f docker-compose.pulse.yml up pulse-api
```

**Environment variables**

- `PULSE_CONFIG` – path to the Pulse configuration file.
- `PULSE_API_KEY` – API key required for authenticated requests.

Service definition: [docker-compose.pulse.yml](docker-compose.pulse.yml).

## ticktobar

Redis stream consumer that aggregates ticks into OHLCV bars for multiple symbols.

**Build and run**

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml build tick-to-bar
docker compose -f docker-compose.yml -f docker-compose.override.yml up tick-to-bar
```

**Environment variables**

- `REDIS_HOST` – Redis host providing tick streams.
- `REDIS_PORT` – Redis port (default `6379`).
- `SYMBOLS` – comma-separated symbols to process.
- `STREAM_VERSION_PREFIX` – stream namespace version (default `v2`).

Service definition: [docker-compose.override.yml](docker-compose.override.yml).

---

## Getting Started – Quick Launch

Before starting, install the core tooling: [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/). Optional dependencies include [Wine](https://wiki.winehq.org/Download) for the MT5 bridge on non-Windows hosts and [Traefik](https://doc.traefik.io/traefik/getting-started/install-traefik/) if you plan to use its routing features.

1. **Clone the repository and set up the environment:**
    ```bash
    git clone https://github.com/fotomash/zanalytics-quant.git
    cd zanalytics-quant
    cp .env.template .env  # Never commit secrets!
    cp backend/mt5/.env.example backend/mt5/.env
    ```

2. **Edit your `.env` and `backend/mt5/.env` files** with all required API keys, passwords, and connection strings. See
   [Environment Variables](#environment-variables) for a summary of the most important settings and
   [docs/env-reference.md](docs/env-reference.md) for the complete table.

The active Docker Compose files are `docker-compose.yml` and optional `docker-compose.override.yml` for local overrides.
Legacy compose configurations have been archived under `docs/legacy/`.

3. **Build and start the platform:**
    ```bash
    docker network create traefik-public
    docker compose build --no-cache
    docker compose up -d
    ```

4. **Apply database migrations:** run `mcp2.sql` to create the `mcp_docs` table and its `created_at` index.
    ```bash
    docker compose exec postgres \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f db/migrations/mcp2.sql
    ```

5. **Check all services:**
    ```bash
    docker compose ps
    docker compose logs dashboard
    docker compose logs mt5
    ```

6. **Access the dashboards and APIs:**
    - **Streamlit Dashboard:**  
      Open `http://localhost:8501` or your mapped domain.
    - **MT5 API:**  
      Try `curl "$MT5_API_URL/ticks?symbol=EURUSD&limit=10"`
    - **Traefik Dashboard:**  
      Open `https://your-traefik-domain.com` (with HTTP auth)
    - **Django API (Swagger/ReDoc):**
      Open `/swagger/` and `/redoc/` endpoints.

---

## Environment Variables

Copy `.env.sample` (or `.env.template` for the full set) to `.env`, fill in the sensitive values, and keep the real
file out of version control. Never commit secrets to the repository. Docker Compose reads `.env` through its `env_file`
directive and injects those variables into services like `mcp`. For deployments, supply these values through your
deployment configuration or a dedicated secrets manager—containers no longer mount `.env` directly.

Key variables to configure before launching:

- `CUSTOM_USER` and `PASSWORD` – MT5 account credentials.
- `MT5_API_URL` / `MT5_URL` – URLs for the MT5 bridge.
- `DJANGO_API_URL` and `DJANGO_API_PREFIX` – Django API endpoints.
- `DASH_METRICS_PATH` and `DASH_PROMPT_PATH` – dashboard configuration paths.
- `BRIDGE_TOKEN` – optional token sent as `X-Bridge-Token` header.
- `VNC_DOMAIN`, `TRAEFIK_DOMAIN`, `TRAEFIK_USERNAME`, `ACME_EMAIL` – domains and Traefik settings.
- `DJANGO_SECRET_KEY` – secret key for Django.
- `MCP2_API_KEY` – secret used by the `mcp` service. Add it to `.env` and Compose
  or CI will inject it; use a 32‑hex‑character value.
- `PINECONE_URL` and `PINECONE_API_KEY` – connection details for the Pinecone
  vector store. Set these to point at your Pinecone deployment or leave the URL
  as `https://localhost:443` to use the local fallback.
- `VECTOR_DB_URL` – base URL for the vector database service (defaults to the
  bundled Qdrant instance).
- `QDRANT_API_KEY` – API key for the Qdrant vector store if auth is required.
- `LOCAL_LLM_MODEL` – model name or path for on‑device LLM inference when
  avoiding external APIs.
- `REDIS_URL` – connection string for the MCP Redis instance.
- `REDIS_STREAMS_URL` – optional Redis dedicated to stream operations
  (falls back to `REDIS_URL`).
- `USE_KAFKA_JOURNAL` – set to `true` to persist journal events in Kafka instead
  of Redis.
- `LOCAL_THRESHOLD` – confidence cutoff for using the local echo model. Ticks
  below this or in spring/distribution phases get a quick `llm_verdict`; others
  queue for Whisperer.

See [docs/README.md](docs/README.md#flags-and-defaults) for default values and
additional notes on these settings.
- `RISK_THRESHOLD` – minimum risk score that triggers high-risk handling in the
  `predict-cron` demo.
- `PREDICT_CRON_INTERVAL`, `PREDICT_CRON_SYMBOL`, `PREDICT_CRON_PRICE`,
  `PREDICT_CRON_RISK`, `PREDICT_CRON_CONFIG` – configure the `predict-cron`
  demo job (interval in seconds, default tick symbol/price/risk, and YAML
  config path).
- `HEALTH_AGGREGATOR_URL` – base URL for the health aggregator queried by the
  dashboard's diagnostics panel.

For the complete list of variables, see [docs/env-reference.md](docs/env-reference.md).

---

### Execution Validation Settings

The engine reads optional execution safeguards from
`config/execution_validation.yaml`:

```yaml
# Execution validation configuration
confidence_threshold: 0.8
fallback_limits:
  max_retries: 3
```

`confidence_threshold` defines the minimum confidence required before an
execution proceeds. Values below this threshold can trigger logic defined in
`fallback_limits`, such as retry limits or alternative handlers.

---

## MT5 service vs. Django API

The MT5 bridge hosts its own REST interface. Django exposes proxies for the MT5 history endpoints, but they simply forward to the MT5 service. To avoid confusion, always point history requests to `MT5_API_URL`.

```bash
curl "$MT5_API_URL/history_deals_get"
curl "$MT5_API_URL/history_orders_get"
```

Directly hitting `$DJANGO_API_URL/history_deals_get` or `$DJANGO_API_URL/history_orders_get` will proxy the call, but the upstream service is still the MT5 bridge.

See [backend/mt5/app/routes/history.py](backend/mt5/app/routes/history.py) for details.

## mt5 vs mt5-api services

The stack uses two related containers:

- **mt5** – runs the MetaTrader 5 bridge and exposes the REST API (including `/ticks`) on port 5001.
- **mt5-api** – a lightweight FastAPI proxy that forwards requests to `mt5` and is typically the entry point for external traffic via Traefik.

Internal services should set `MT5_API_URL` to `http://mt5:5001` so they speak directly to the bridge that serves tick data.

## How It Works (Practical Flow)

Step-by-step data flow from MT5 to the dashboard. [Read more](docs/how_it_works.md).

---

## Data Integrity and Deduplication

Tick data is hashed with MD5 to prevent duplicates and ensure consistency. [Details](docs/md5_flow.md).

---

## MT5 Bridge & Orders (Execution)

Core endpoints handle market orders, partial closes, scaling, and hedging. See [docs/POSITIONS_AND_ORDERS.md](docs/POSITIONS_AND_ORDERS.md).

---

## Actions Bus for GPT (≤30 operations)

Single endpoint for GPT-driven verbs defined in `openapi.actions.yaml`. Deep dive in [docs/ACTIONS_BUS.md](docs/ACTIONS_BUS.md).

---

## Dashboards & Diagnostics

Streamlit pages under `dashboard/pages/` power Pulse, Whisperer, and diagnostics. `24_Trades_Diagnostics.py` compares closed trades, MT5 history, and open positions. See [`dashboard/`](dashboard/README.md) for setup and [`dashboards/`](dashboards/README.md) for standalone examples.

---

## Journaling (ZBAR)

Structured entries append via `/api/v1/journal/append`. Schema and guide in [docs/JOURNALING.md](docs/JOURNALING.md).

---

## Typical User Scenarios

Examples of real-time viewing, enrichment jobs, and troubleshooting. [docs/user_scenarios.md](docs/user_scenarios.md).

---

## Data Enrichment & Customization

Extend scripts in `utils/` to build custom features and dashboards. [Workflow](docs/data_enrichment_customization.md).

## Session Manifest Prompts

The session manifest bundles reusable Whisperer prompts:

- `aware_caution_v1` — Reinforces situational awareness and caution during volatile phases.
- `what_if_surge_masks_trap_v1` — Considers whether a rapid surge might conceal a trap.
- `guardrail_evolution_v1` — Guides adjustments to risk guardrails as market conditions change.

## Confidence Trace Matrix

`confidence_trace_matrix.json` at the repository root configures staged confidence scoring. Each stage includes a numeric `weight` and a `bounds` object with `min` and `max` values:

- **raw_calculation** – base confidence derived from raw signals.
- **simulation_adjustment** – modifies that score using simulated scenarios.
- **normalize** – scales the adjusted value to a standard range.
- **ensemble_contribution** – blends confidence across multiple models.

Weights typically sum to 1.0 and bounds constrain each stage's output.

---

## Example .env Configuration

Sample settings are available in [docs/example-env.md](docs/example-env.md).

---

## Security & Access Control

- **Traefik reverse proxy** provides SSL and HTTP Basic Auth at entrypoints.
- All APIs require authentication and rate limits are applied.
- Data flows are segmented per Docker network for defense in depth.

## API Health Check and Query Examples

Check basic server health (no authentication required):

```bash
curl -s http://localhost:8080/health
```

Query the Actions Bus with both required headers and a valid JSON body:

```bash
curl -sX POST http://localhost:8080/api/v1/actions/query \
  -H "Authorization: Bearer dev-key-123" \
  -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"type":"session_boot","payload":{"user_id":"demo"}}'
```

The `Content-Type: application/json` header is mandatory when submitting JSON payloads.

---

## Contributing

This codebase is not open for external contributions. All changes are managed internally with strict audit and review.

---

## Running Tests

Commands for Django and analyzer suites are in [docs/running_tests.md](docs/running_tests.md).

---

## Known Issues & Best Practices

Current limitations and extension tips: [docs/known_issues_best_practices.md](docs/known_issues_best_practices.md).

---

## Future Directions & Next Steps

Planned improvements include live data ingestion, Redis-first caching, decoupled enrichment, and OAuth2 security. [Full roadmap](docs/future_directions.md).

---

## License

**All logic, infrastructure, dashboards, enrichment scripts, data models, and code are strictly proprietary and protected IP.**

Unauthorized use, distribution, or copying is prohibited and will be prosecuted.

This project is proprietary and provided under a strict, non-transferable license. See [LICENSE](LICENSE) for details.

---

## Advanced Usage

Add new Streamlit dashboards following [docs/advanced_dashboard.md](docs/advanced_dashboard.md).

---

## Kafka Replay Consumer

Replay historical ticks or bars from Kafka into a datastore for analysis.
The script's entry point is the ``main`` function inside
``ops/kafka/replay_consumer.py``.

### Basic usage

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC=ticks.BTCUSDT
python ops/kafka/replay_consumer.py --start-offset 0 --batch-size 100
```

For batch processing of entire poll results use:

```bash
python ops/kafka/replay_consumer.py --mode batch
```

Arguments may be set via environment variables (`KAFKA_TOPIC`,
`KAFKA_START_OFFSET`, `KAFKA_BATCH_SIZE`, `KAFKA_CONSUMER_MODE`) or passed on
the command line.

### Replay into Redis

Customize the ``process_messages`` function in
``ops/kafka/replay_consumer.py`` to push payloads into Redis:

```python
import redis

r = redis.Redis.from_url("redis://localhost:6379/0")

def process_messages(messages):
    for msg in messages:
        if not msg.error():
            r.lpush("ticks", msg.value())
```

### Replay into Postgres

Use ``psycopg2`` or similar to insert records:

```python
import psycopg2

def process_messages(messages):
    with psycopg2.connect("postgresql://user:pass@localhost/db") as conn:
        with conn.cursor() as cur:
            for msg in messages:
                if not msg.error():
                    cur.execute("INSERT INTO ticks(raw) VALUES (%s)", (msg.value(),))
        conn.commit()
```

These examples write raw messages; adapt the logic for your schema and
types when storing bars or ticks for downstream analysis.

---

## Full API Documentation

- **Swagger:** `/swagger/`
- **ReDoc:** `/redoc/`
- Generate Python module docs with:
  ```bash
  pdoc --html utils --output-dir docs/api
  ```

---

## FAQ

Common setup and operational questions live in [docs/faq.md](docs/faq.md).

**Q: Something isn’t working—how do I see detailed error logs?**
A: Use `docker compose logs <service>` (add `-f` to follow in real time) or `docker logs <container>` for single containers. For service-specific errors, check Django's debug logs and MT5 bridge logs.

**Q: Can I run this without Docker?**
A: Not recommended. The MT5 and dashboard stack is designed for containerization for full reproducibility and security.

**Q: Where is my live data stored?**  
A: Real-time data is cached in Redis and long-term data is stored in Postgres. Snapshots/exports may use Parquet in `/data/`.

**Q: How can I add a new feature or signal?**  
A: Extend or edit the scripts in `utils/` and trigger the enrichment process.

**Q: What if the dashboard is blank?**
A: Double-check your API/DB containers, verify enrichment, and confirm `.env` credentials.


**Q: I receive errors about missing environment variables.**
A: Copy `.env.example` to `.env`, double-check the keys, and restart the containers after any updates.


**Q: The app can't connect to Postgres or Redis.**
A: Confirm your `.env` credentials, ensure the services are running (`docker ps`), and check container logs for authentication or network errors.

**Q: Why is Whisperer showing trades from yesterday?**
A: MetaTrader likely didn’t boot—ensure Wine and required DLLs are available, then run `wine mt5.exe &` from the mounted volume or alias it in `startup.sh`. Verify readiness with `docker logs mt5`.

**Q: How do I clear cached data in Redis?**
A:
1. Run the following to flush all cached keys:
   ```bash
   docker compose exec redis redis-cli FLUSHALL
   ```
2. Restart the services so caches repopulate with fresh data.

**Q: I need a clean database—how do I reset Postgres?**
A:
1. Stop the services:
   ```bash
   docker compose down
   ```
2. Remove the Postgres volume (be sure you're ok losing all data):
   ```bash
   docker volume rm <name>  # or docker compose down -v
   ```
3. Rerun migrations to recreate schema:
   ```bash
   docker compose run django migrate
   ```
4. Restart the stack:
   ```bash
   docker compose up -d
   ```

**Q: Docker containers fail to build/start.**
A:
1. Verify your Docker installation and version.
2. Rebuild images without cache using `docker compose build --no-cache`.
3. Check container output with `docker compose logs`.
4. Ensure required ports are free to avoid conflicts.

**Q: Docker containers complain about file or directory permissions.**
A: Verify host permissions on the affected paths. Run `sudo chown -R $USER:$USER <path>` or adjust with `chmod`, then rebuild the containers to apply the changes.

**Q: Startup fails with "address already in use."**
A: Another service is already bound to a required port.

1. Run `lsof -i :<port>` or `netstat -tulpn` to find the PID and service using the port.
2. Stop the offending process (`kill <PID>` or `systemctl stop <service>`).
3. Or edit the `ports:` mapping in `docker-compose.yml` to use a free port and restart the stack.

**Q: MCP silent or `curl` 404s, but logs are empty?**
A: The `pulse-api` service is likely hijacking port `8001`. Stop it and recreate the MCP container:

```bash
docker stop pulse-api tick-to-bar 2>/dev/null || true
docker compose up --force-recreate mcp
```

Then test the endpoint:

```bash
curl -k https://mcp1.zanalytics.app/mcp | head -3
```

You should see `{"event": "open", ...}`.

**Q: Install or build fails due to missing packages or version conflicts?**
A: Ensure you're using the supported Python version, then install dependencies with `poetry install` or `pip install -r requirements.txt`. If issues persist, clear cached wheels (e.g., `pip cache purge`) and try again.

**Q: The web UI won't compile or `npm start` fails.**
A: Remove the `web/node_modules` directory and reinstall dependencies with `npm install` (or `npm ci`). Ensure you're using the project's required Node.js version.


**Q: Celery tasks are stuck or failing—what should I do?**
A:
1. Check the Celery worker logs for errors.
2. Purge the queue:
   ```bash
   celery -A app purge -f
   ```
3. Restart the Celery service.
4. For a quick diagnostic, run [check_celery.sh](check_celery.sh).

**Q: How do I reset the containers when data gets corrupted or outdated?**
A:
1. Stop and remove containers and volumes: `docker compose down -v`.
2. Remove any orphan containers: `docker container prune -f`.
3. Rebuild and start fresh containers: `docker compose up --build`.
4. Rerun database migrations if applicable.


## Troubleshooting Gold Mine

See [docs/mcp_troubleshooting.md](docs/mcp_troubleshooting.md) for Traefik label requirements, keychain unlock steps, and ghost container cleanup specific to the MCP server.


1. First sign of death: Whisperer says stopped talking to connector. Curl to /mcp gives heartbeat → MCP alive. Curl to /exec gives 404. → Traefik not routing. Added traefik.http.routers.mcp.rule=Host(mcp1.zanalytics.app) and port 8001:8001 → still 404.
2. Localhost test: curl http://localhost:8001/exec → connection refused. → Port not exposed. Added ports: - 8001:8001 in compose → now connects, but still 404.
3. Auth 401: curl -H "Authorization: Bearer your-dev-secret-123" -H "X-API-Key: your-dev-secret-123" → Unauthorized. → Env var wrong name. Code uses MCP2_API_KEY, not API_KEY. Fixed .env → restart mcp → still 401. → Restart doesn't reload env in FastAPI. Had to --build the container to pick up MCP2_API_KEY=your-dev-secret-123.
4. Still 404 after auth works: Endpoint name wrong. Code has @app.post(/exec) but Whisperer hits /api/v1/actions/query. → Not our fault-Whisperer's connector config was hardcoded to old path. Updated connector to match real route: /exec.
5. Pop-up hell: Whisperer says requires approval. → MCP middleware blocks unless approve:true sent. Added flag, updated curl, merged PR 241. Now auto-approves boot & equity.
6. Wine/MetaTrader feed dead: Whisperer shows yesterday's trades. → MT5 popped resolution dialog, never clicked. Had to manually OK after reboot → feed starts. Documented in FAQ as manual step.
7. Ghost containers eating ports: docker ps shows pulse-api, tick-to-bar on 8001. → docker stop pulse-api tick-to-bar → mcp binds clean. End result: curl -k -H "Authorization: Bearer your-dev-secret-123" -H "X-API-Key: your-dev-secret-123" -X POST https://mcp1.zanalytics.app/exec -d '{"type":"session_boot","approve":true}' → returns real equity, positions, risk. Whisperer loads without pop-up. Save this. Every time something breaks, start here-no bush, no circles.

## MCP2 Runbook

For startup commands, endpoint tests, and database maintenance, see the [MCP2 Runbook](docs/runbooks/mcp2.md).

---

## Pulse Dashboard Prototype

Behavioral and risk analytics demo. [docs/pulse_dashboard_prototype.md](docs/pulse_dashboard_prototype.md).

---

## Further Reading

- [Pulse README](README_PULSE.md)
- [Pulse Wyckoff Live README](PULSE_WYCKOFF_LIVE_README.md)
- [Documentation Hub](docs/README.md)
- [Pulse Integration Plan](PULSE_INTEGRATION_PLAN.md)
- [Stakeholder Update](ZANALYTICS_PULSE_STAKEHOLDER_UPDATE.md)
