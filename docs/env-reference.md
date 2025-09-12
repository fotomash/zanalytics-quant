# Environment Variable Reference

This document lists the environment variables defined in [`.env.template`](../.env.template).
Start by copying that template to a new `.env` file and filling in your own secrets.
**Never commit the populated `.env` file to version control.**

For local development, Docker Compose reads `.env` via its `env_file` directive and
injects the values into services like `mcp`. In CI environments, provide the same
variables through your pipeline's environment or secret store. The container no
longer mounts `.env` directly.

Values defined in `.env` or in the shell environment override the defaults shown here.

## Core Database Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `POSTGRES_DB` | `zanalytics` | Change to use a different database name. | PostgreSQL database holding core application data. |
| `POSTGRES_USER` | `postgres` | Set to the username that exists in your database server. | Username for connecting to PostgreSQL. |
| `POSTGRES_PASSWORD` | `your_secure_postgres_password_here` | Replace with the actual user password. | Password for the PostgreSQL user. |
| `POSTGRES_HOST` | `postgres` | Adjust if the database runs on another host. | Hostname of the PostgreSQL server. |
| `POSTGRES_PORT` | `5432` | Change if PostgreSQL listens on a non‑default port. | TCP port for the PostgreSQL server. |

## Redis Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `REDIS_URL` | `redis://redis:6379/0` | Modify to point at a different Redis instance/DB. | Connection URL used by services that expect a Redis URI. |
| `REDIS_HOST` | `redis` | Change when Redis runs on another host. | Hostname of the Redis server. |
| `REDIS_PORT` | `6379` | Adjust if Redis listens on a different port. | TCP port for the Redis server. |
| `STREAM_VERSION_PREFIX` | `v2` | Change to adjust Redis stream namespace. | Version prefix for Redis stream keys (e.g., `v2:ticks:*`). |
| `SESSION_BOOT_TTL` | `30` | Set to control session bootstrap cache lifetime in seconds. | Time‑to‑live for session bootstrap cache entries. |
| `TRADES_RECENT_TTL` | `15` | Change to tune how long recent trades stay cached. | Cache TTL for recent trades in seconds. |
| `RISK_STATUS_TTL` | `20` | Adjust to control risk status cache duration. | Cache TTL for risk status values in seconds. |

## Kafka Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Change to point at a different Kafka broker. | Bootstrap servers for Kafka producers and consumers. |
| `KAFKA_GROUP_ID` | `zanalyzer` | Set to run consumers under a different group. | Default consumer group id used by Kafka utilities. |

## Django Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | `your-super-secret-django-key-change-this-in-production` | Replace with a secure random string in production. | Secret key for Django's cryptographic signing. |
| `DJANGO_SETTINGS_MODULE` | `app.settings` | Change to use a different settings module. | Python module path to Django settings. |
| `DJANGO_DOMAIN` | `django.localhost` | Update to the domain serving the Django app. | Hostname used by Django for site URLs. |
| `DJANGO_API_URL` | `http://django:8000` | Modify if the Django API is accessible elsewhere. | Base URL for the Django REST API. |
| `DJANGO_API_PREFIX` | `/api/v1` | Adjust if the API prefix changes. | Root path prefix for Django API endpoints. |
| `INTERNAL_API_BASE` | `http://django:8000` | Override to point at a different internal Django API host. | Base URL the MCP server uses when proxying `/exec` requests to Django. |
| `MCP2_API_KEY` | _(empty)_ | Set to a strong secret in production. | API key the MCP server expects in `X-API-Key` header. |

## Frontend / Dashboard Defaults
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `PULSE_DEFAULT_SYMBOL` | `XAUUSD` | Change to set a different default trading symbol. | Fallback market symbol for Streamlit pages. |
| `PULSE_PLAYBOOK_PATH` | _(empty)_ | Provide a path to use a custom Pulse playbook file. | Overrides the default Pulse playbook location. |
| `ZAN_CACHE_DIR` | _(empty)_ | Set to force dashboards to use a specific cache directory. | Directory for caching dashboard data. |
| `PULSE_CONF_WEIGHTS` | _(empty)_ | Supply JSON to customize Pulse confluence weights. | Overrides internal default weighting for Pulse signals. |
| `HEALTH_AGGREGATOR_URL` | `http://localhost:8000/health` | Set to the URL of the health aggregator service. | Base URL the diagnostics panel queries for system health. |

## Traefik & SSL Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `TRAEFIK_DOMAIN` | `traefik.localhost` | Change to the domain hosting the Traefik dashboard. | Domain served by Traefik. |
| `TRAEFIK_USERNAME` | `admin` | Adjust to set a different admin username. | Username for Traefik dashboard basic auth. |
| `TRAEFIK_HASHED_PASSWORD` | `$$2y$$10$$example_hash_replace_this` | Replace with an htpasswd‑generated hash. | Hashed password for Traefik dashboard access. |
| `ACME_EMAIL` | `your-email@example.com` | Set to the email used for ACME/Let's Encrypt registration. | Contact email for certificate issuance. |

## Domain Mappings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `VNC_DOMAIN` | `vnc.localhost` | Change if exposing VNC under another domain. | Domain mapping for the VNC service. |
| `API_DOMAIN` | `api.localhost` | Modify to match the deployed API domain. | Domain mapping for the public API. |
| `DASHBOARD_DOMAIN` | `dash.localhost` | Set to the domain used for dashboards. | Domain mapping for the dashboard UI. |
| `GRAFANA_DOMAIN` | `grafana.localhost` | Change if Grafana is hosted elsewhere. | Domain mapping for the Grafana interface. |
| `INFO_DOMAIN` | `info.localhost` | Adjust to map the informational site. | Domain mapping for the info site. |

## MT5 Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `MT5_API_URL` | `http://mt5:5001` | Change if the MT5 bridge runs elsewhere. | Base URL for MT5 API requests. |
| `MT5_API_BASE` | `http://mt5:5001` | Adjust when the base URL differs from the API URL. | Root URL for MT5 API endpoints. |
| `CUSTOM_USER` | `your_mt5_username` | Set to your MT5 account username. | Username for authenticating with MT5. |
| `PASSWORD` | `your_mt5_password` | Replace with the MT5 account password. | Password for the MT5 account. |
| `MT5_HEARTBEAT_INTERVAL` | `30` | Change to control heartbeat frequency in seconds. | Interval between MT5 gateway heartbeat messages. |
| `MT5_HEARTBEAT_ALERT_THRESHOLD` | `90` | Adjust to tune downtime alerts in seconds. | Time without heartbeat before an alert is triggered. |

## Pulse Kernel Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `PULSE_API_URL` | `http://django:8000` | Modify if the Pulse API lives at a different URL. | Endpoint used by the Pulse kernel. |
| `PULSE_CONFIG` | `/app/pulse_config.yaml` | Set to point at an alternate configuration file. | Path to the Pulse kernel configuration. |
| `PULSE_JOURNAL_PATH` | `/app/data/journal` | Change to store journal entries elsewhere. | Directory where Pulse journals are stored. |

## Streamlit Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `STREAMLIT_SERVER_PORT` | `8501` | Adjust if you want the main dashboard on another port. | Port for the primary Streamlit dashboard server. |

## Info site
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `WIKI_DASHBOARD_PORT` | `8503` | Change to host the secondary dashboard on another port. | Port for additional UAT/info dashboards. |

## Orchestrator / Actions Client
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `API_URL` | `http://localhost:8010` | Set to the URL of the orchestrator/actions API. | Endpoint used by scripts/tests to interact with actions. |
| `API_TOKEN` | _(empty)_ | Provide a token to enable authenticated requests. | Authentication token for the orchestrator API. |

## LLM Routing
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `LOCAL_THRESHOLD` | `0.6` | Raise or lower to adjust when ticks are sent to Whisperer. | Confidence cutoff for local echo vs. remote Whisperer processing. |
| `LOCAL_LLM_MODEL` | `llama3:8b-instruct` | Set to the model name served by Ollama or similar. | Model used for on-box inference. |

## Vector Store Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `VECTOR_DB_URL` | `http://qdrant:6333` | Change to point at a different vector database. | Base URL for the vector store (Qdrant). |
| `QDRANT_API_KEY` | _(empty)_ | Provide if your vector DB requires authentication. | API key for the vector database. |

## Celery Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `CELERY_APP` | `app` | Change if the Celery application module is different. | Celery application name used by workers. |
| `CELERY_CONCURRENCY` | `3` | Adjust to control number of worker processes. | Concurrency level for Celery workers. |

## Discord Notifications
Environment variables consumed by the Pulse Discord bot
[`services/pulse_bot/bot.py`](../services/pulse_bot/bot.py).

| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `DISCORD_BOT_TOKEN` | `your_discord_bot_token_here` | Replace with your bot token to enable notifications. | Token used to authenticate with the Discord Bot API. |
| `DISCORD_CHANNEL_WHITELIST` | _(empty)_ | Comma-separated channel IDs permitted to issue commands. | Restricts bot commands to approved channels. |
| `DISCORD_CHANNEL_ID` | `your_discord_channel_id_here` | Set to the channel ID that should receive messages. | Destination channel for Discord alerts. |

## Alert Settings
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `ALERTS_ENABLED` | `true` | Set to `false` to disable alerting. | Master switch for the alerts subsystem. |
| `ALERTS_MIN_INTERVAL_SECONDS` | `60` | Change to rate‑limit alert frequency. | Minimum seconds between alerts. |
| `ALERTS_SCORE_HI` | `90` | Adjust threshold for high‑score alerts. | Minimum score to trigger an alert. |
| `ALERTS_TOXICITY_LIMIT` | `0.30` | Tune to cap toxicity levels allowed. | Maximum acceptable toxicity before alerting. |
| `ALERTS_DD_INTRADAY_WARN` | `0.025` | Change to control drawdown warning level. | Intraday drawdown fraction that triggers a warning. |

## Monitoring Ports
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `PROMETHEUS_PORT` | `9090` | Adjust if Prometheus should listen on a different port. | Port where Prometheus serves metrics. |
| `ALERTMANAGER_PORT` | `9093` | Change if Alertmanager should listen on another port. | Port for the Alertmanager web UI and API. |
| `GRAFANA_PORT` | `3000` | Set to expose Grafana on an alternate port. | Port for accessing the Grafana dashboard. |

## Monitoring Versions
| Variable | Default | Override Behavior | Purpose |
| --- | --- | --- | --- |
| `GRAFANA_VERSION` | `11.0.0` | Set to use a different Grafana container version. | Version tag for Grafana. |
| `PROMETHEUS_VERSION` | `v2.42.0` | Change to pull another Prometheus version. | Version tag for Prometheus. |
| `CADVISOR_VERSION` | `v0.46.0` | Adjust to select a different cAdvisor version. | Version tag for cAdvisor. |
| `NODE_EXPORTER_VERSION` | `v1.5.0` | Modify to use another Node Exporter release. | Version tag for node-exporter. |
| `ALERTMANAGER_VERSION` | `v0.25.0` | Change to pull a different Alertmanager version. | Version tag for Alertmanager. |

