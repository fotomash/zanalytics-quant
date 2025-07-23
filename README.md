# Zanalytics Quant Platform

> **Strictly proprietary and protected IP. For authorized use only.**

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [System Overview](#system-overview)
- [Getting Started – Quick Launch](#getting-started--quick-launch)
- [How It Works (Practical Flow)](#how-it-works-practical-flow)
- [Data Integrity and Deduplication: MD5 Flow](#data-integrity-and-deduplication-md5-flow)
- [Typical User Scenarios](#typical-user-scenarios)
- [Data Enrichment & Customization](#data-enrichment--customization)
- [Example .env Configuration (Partial)](#example-env-configuration-partial)
- [Security & Access Control](#security--access-control)
- [Contributing](#contributing)
- [Known Issues & Best Practices](#known-issues--best-practices)
- [Future Directions & Next Steps](#future-directions--next-steps)
- [License (Strict, Non-Transferable)](#license-strict-non-transferable)
- [Advanced Usage: Adding a New Dashboard](#advanced-usage-adding-a-new-dashboard)
- [Full API Documentation](#full-api-documentation)
- [FAQ](#faq)

---

## Overview

**Zanalytics Quant** is a proprietary, IP-protected quant trading and data analysis platform built for professional and in-house research use.  
It leverages MetaTrader 5 (MT5), Django, Streamlit, Redis, Postgres, and custom enrichment pipelines to power live and historical financial dashboards and APIs.

---

## Architecture

This platform is multi-container and modular, designed for reliability, security, and easy extensibility.

```mermaid
graph LR
    subgraph Core
        MT5[MT5 (Docker/Wine)] -- Market Data/API --> DjangoAPI[Django API]
        DjangoAPI -- REST/WS --> Dashboard[Streamlit Dashboard]
        Dashboard -- Fetch/Stream --> DjangoAPI
        DjangoAPI -- ORM --> Postgres[(Postgres)]
        DjangoAPI -- Cache --> Redis[(Redis)]
        Enrichment[Enrichment Scripts (utils/)] -- ETL/Batch --> Postgres
        Enrichment -- Cache --> Redis
        MT5 -- CSV/Parquet --> Enrichment
    end
```

**Components:**
- **MT5**: Runs MetaTrader 5 via Wine in Docker; exposes HTTP/REST API.
- **Django API**: Handles authentication, orchestration, REST endpoints, and DB sync.
- **Redis**: Fast in-memory store for real-time tick/bars, event streams, and enrichment cache.
- **Postgres**: Main DB for tick, bar, position, and enrichment data.
- **Enrichment Scripts**: Python scripts (`utils/`) for data ETL, aggregation, feature generation, and historical sync.
- **Streamlit Dashboard**: User UI for analytics, charts, and operations.

---

## System Overview

The Zanalytics Quant platform is architected to meet the rigorous demands of professional quantitative research and trading. Each component has a distinct role designed to maximize security, modularity, and performance:

- **MT5** serves as the primary market data source and trading engine, running inside a Docker container with Wine to ensure consistent cross-platform operation. It exposes a REST API for data retrieval and order management, isolating the trading environment from other system components for security and stability.

- **Django API** acts as the orchestrator and backend service layer. It manages user authentication, enforces access controls, and provides RESTful endpoints for data retrieval and command execution. The API encapsulates business logic and database interactions, ensuring secure and auditable operations.

- **Redis** is leveraged as a high-performance in-memory cache and message bus. It stores real-time tick and bar data, event streams, and intermediate enrichment results to enable low-latency analytics and dashboard updates. Redis caching reduces load on the main database and supports real-time responsiveness.

- **Postgres** is the authoritative data store for all historical and enriched market data, including ticks, bars, positions, and computed features. It provides transactional integrity and supports complex queries required for backtesting and research.

- **Enrichment Scripts** located in the `utils/` directory perform data transformation, feature engineering, and batch ETL processes. They convert raw market data into actionable alpha features, rolling statistics, and signals, which are then persisted back to Postgres and cached in Redis.

- **Streamlit Dashboard** offers a user-friendly, interactive frontend for visualization and analysis. It consumes data from the Django API and Redis cache, presenting live and historical market insights with customizable charts and controls.

This modular design facilitates secure separation of concerns, easy extensibility for new features or data sources, and robust performance for professional quant workflows.

---

## Getting Started – Quick Launch

1. **Clone the repository and set up the environment:**
    ```bash
    git clone https://github.com/fotomash/zanalytics-quant.git
    cd zanalytics-quant
    cp .env.example .env  # Never commit secrets!
    cp backend/mt5/.env.example backend/mt5/.env
    ```

2. **Edit your `.env` and `backend/mt5/.env` files** with all required API keys, passwords, and connection strings.
   You need:
    - All database credentials
    - Redis settings
    - Domain names for Traefik routing
    - MT5 and Django/Flask endpoints

3. **Build and start the platform:**
    ```bash
    docker-compose build --no-cache
    docker-compose up -d
    ```

4. **Check all services:**
    ```bash
    docker-compose ps
    docker-compose logs dashboard
    docker-compose logs mt5
    ```

5. **Access the dashboards and APIs:**
    - **Streamlit Dashboard:**  
      Open `http://localhost:8501` or your mapped domain.
    - **MT5 API:**  
      Try `curl "$MT5_API_URL/ticks?symbol=EURUSD&limit=10"`
    - **Traefik Dashboard:**  
      Open `https://your-traefik-domain.com` (with HTTP auth)
    - **Django API (Swagger/ReDoc):**  
      Open `/swagger/` and `/redoc/` endpoints.

---

- `CUSTOM_USER`: Username for accessing the MT5 service.
- `PASSWORD`: Password for the custom user.
- `VNC_DOMAIN`: Domain for accessing the VNC service.
- `TRAEFIK_DOMAIN`: Domain for Traefik dashboard.
- `TRAEFIK_USERNAME`: Username for Traefik basic authentication.
- `ACME_EMAIL`: Email address for Let's Encrypt notifications.
- `MT5_API_URL`: Base URL where the MT5 service is available (e.g., `http://mt5:5001`).
- `DJANGO_API_URL`: Base URL of the Django API service (e.g., `http://django:8000`).
- `DJANGO_API_PREFIX`: Path prefix for all Django API endpoints (default `/api/v1`).
- `DJANGO_SECRET_KEY`: Secret key for the Django application. **Required.** c859abdafe2b06c03292270351066a2041e1452c


## How It Works (Practical Flow)

### 1. **Data Pipeline**
- **MT5** runs inside Docker (with Wine if on Linux/Mac) and streams live tick/bar/position/order data via REST API.
- **Django/Flask** container handles user authentication, business logic, and all database ops.
- **Enrichment Scripts** (in `utils/`) transform raw market data into alpha features, rolling stats, signals, and are responsible for ETL (Extract, Transform, Load).
- **Postgres** stores all historical and enriched market data.
- **Redis** is used for real-time, super-fast caching (e.g. tickers, rolling windows).
- **Streamlit Dashboard** presents analytics and charts, pulling live from APIs or historical DB/Parquet as configured.

---

## Data Integrity and Deduplication: MD5 Flow

To ensure data integrity and prevent duplication of tick data, the platform employs an MD5 hashing mechanism as part of its enrichment and caching workflow. Each incoming tick is serialized and hashed using MD5, producing a unique fingerprint that represents the tick's content.

This MD5 hash is then used within the enrichment scripts (notably within components like `TickVectorizer`) to detect duplicate ticks before insertion into the database or cache. By comparing incoming tick hashes against existing entries in Redis or Postgres, the system avoids redundant processing and storage, which is critical for maintaining accurate real-time analytics.

This approach improves both data quality and system efficiency, ensuring that dashboards and APIs reflect consistent, deduplicated market data streams.

---

## Typical User Scenarios

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

### d) **Troubleshooting**
- Dashboard blank?  
  Check the API/DB container logs, ensure enrichment is running, and verify `.env` secrets.
- MT5 error?  
  Make sure Wine is running and your license/user is set in the `.env`.

---

## Data Enrichment & Customization

- **Modify or extend enrichment scripts** in `utils/` to calculate your own custom features.
- Run enrichment as a scheduled job, via cron, or as a service container.
- You can create new dashboards by adding new `.py` files in the `dashboard/` folder and referencing new data sources (DB, Redis, Parquet).

### Example Enrichment Workflow

A typical enrichment workflow begins with raw tick data streamed from MT5 or loaded from CSV/Parquet snapshots. Each tick is processed by enrichment scripts in `utils/` which perform the following steps:

1. **Transformation:** The raw tick is parsed and normalized (e.g., timestamp conversion, price adjustments).
2. **Hashing:** The tick is hashed with MD5 to detect duplicates.
3. **Storage:** Unique ticks are inserted into Postgres for long-term storage and cached in Redis for fast access.
4. **Feature Generation:** Rolling statistics, indicators (such as SMA, RSI), and signals are computed over the tick and bar data.
5. **Caching:** Computed features are cached in Redis to support low-latency dashboard queries.
6. **Visualization:** The Streamlit dashboard fetches enriched data from the Django API, which queries both Postgres and Redis, to render charts and analytics in near real-time.

This pipeline ensures that enriched data remains consistent, performant, and extensible for custom quant research.

---

## Example .env Configuration (Partial)

```env
# Platform credentials
CUSTOM_USER=your_user
PASSWORD=super_secret_password

# MT5 and API endpoints
MT5_API_URL=http://mt5-api:8050
DJANGO_API_URL=http://django-api:8000
DJANGO_API_PREFIX=/api/v1

# Database config
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=zanalytics

# Redis config
REDIS_HOST=redis
REDIS_PORT=6379

# Traefik/SSL/Domains
VNC_DOMAIN=your-vnc-domain.com
TRAEFIK_DOMAIN=your-traefik-domain.com
TRAEFIK_USERNAME=admin
ACME_EMAIL=your@email.com
```
> *Never check in your production .env or real keys!*

---

## Security & Access Control

- **Traefik reverse proxy** provides SSL and HTTP Basic Auth at entrypoints.
- All APIs require authentication and rate limits are applied.
- Data flows are segmented per Docker network for defense in depth.

---

## Contributing

This codebase is not open for external contributions.  
All changes are managed internally, with strict audit and review.

---

## Known Issues & Best Practices

### Known Issues
- **Environment Handling:** Care must be taken to secure `.env` files and avoid committing secrets to version control.
- **Error Handling:** Some enrichment scripts may require improved exception management for robustness, especially with live data streams.
- **Modularity:** While modular, some components have implicit dependencies that should be documented and refactored over time.

### Best Practices for Extension
- Always include comprehensive docstrings for new scripts and functions.
- Document any new API endpoints with clear schema definitions.
- Avoid hardcoding secrets or credentials; use environment variables exclusively.
- Follow existing code style and architectural patterns to maintain consistency.
- Test new features thoroughly in isolated environments before deployment.

---

## Future Directions & Next Steps

We plan to enhance the platform with the following improvements:

- **Live Data Ingestion:** Streamline MT5 data ingestion to support higher throughput and lower latency.
- **Redis-first Caching:** Shift more data queries to Redis for real-time responsiveness, reducing Postgres load.
- **Decoupling Enrichment:** Separate enrichment pipelines from the dashboard layer to allow independent scaling and scheduling.
- **Enhanced API Security:** Implement OAuth2 and token-based authentication for finer-grained access control and auditability.

These steps aim to improve scalability, security, and flexibility for professional quant workflows.

---

## License (Strict, Non-Transferable)

**All logic, infrastructure, dashboards, enrichment scripts, data models, and code are strictly proprietary and protected IP.**  
Unauthorized use, distribution, or copying is prohibited and will be prosecuted.

---

## Advanced Usage: Adding a New Dashboard

1. **Create a new Python file** in `dashboard/` (e.g. `CustomDashboard.py`).
2. **Import data** from the Django API, Redis, or load a Parquet snapshot.
3. **Add custom Streamlit widgets, charts, or analytics.**
4. **Mount in Docker, rebuild, and access from the dashboard UI.

---

## Full API Documentation

- **Swagger:** `/swagger/`
- **ReDoc:** `/redoc/`

> Note: The Swagger and ReDoc endpoints may not be present in all deployments depending on configuration. If these are not exposed, you can generate API documentation locally using Django REST Framework's built-in schema generation tools or third-party packages such as `drf-yasg` or `pdoc`.  
>  
> API endpoints require authentication and are accessible only to authorized users. Ensure your credentials and tokens are properly configured before making requests.

- **Python module docs:**  
  Generate with pdoc:
    ```bash
    pdoc --html utils --output-dir docs/api
    ```

- **Enrichment API and scripts:**  
  Document your scripts with docstrings for easier internal use.

---

## FAQ

**Q: Can I run this without Docker?**  
A: Not recommended. The MT5 and dashboard stack is designed for containerization for full reproducibility and security.

**Q: Where is my live data stored?**  
A: Real-time data is cached in Redis and long-term data is stored in Postgres. Snapshots/exports may use Parquet in `/data/`.

**Q: How can I add a new feature or signal?**  
A: Extend or edit the scripts in `utils/` and trigger the enrichment process.

**Q: What if the dashboard is blank?**  
A: Double-check your API/DB containers, verify enrichment, and confirm `.env` credentials.

---

Let me know if you want even deeper detail—*e.g.*, specific API endpoint schemas, more onboarding workflows, or internal architecture diagrams.
