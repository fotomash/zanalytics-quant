# Example .env Configuration (Partial)

See [Environment Variables](../README.md#environment-variables) for descriptions and the full reference table.

```env
# Platform credentials
CUSTOM_USER=your_user
PASSWORD=super_secret_password

# MT5 and API endpoints
MT5_URL=http://mt5:5001
MT5_API_URL=http://mt5:5001
DJANGO_API_URL=http://django:8000
DJANGO_API_PREFIX=/api/v1
DJANGO_DEBUG=false
BRIDGE_TOKEN=

# Dashboard config
DASH_METRICS_PATH=dashboard/config/dashboard_metrics_summary.yaml
DASH_PROMPT_PATH=dashboard/config/dashboard_prompt.txt

# Database config
# Set POSTGRES_PASSWORD to a strong value; no default is provided.
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_postgres_password_here
POSTGRES_DB=zanalytics

# Redis config
REDIS_HOST=redis
REDIS_PORT=6379

# Vector store config
VECTOR_DB_URL=http://qdrant:6333
QDRANT_API_KEY=

# Local model served via Ollama or similar
LOCAL_LLM_MODEL=llama3:8b-instruct

# Journal persistence
PULSE_JOURNAL_PATH=/app/data/journal
USE_KAFKA_JOURNAL=false

# Traefik/SSL/Domains
VNC_DOMAIN=your-vnc-domain.com
TRAEFIK_DOMAIN=your-traefik-domain.com
TRAEFIK_USERNAME=admin
ACME_EMAIL=your@email.com
```

> *Never check in your production .env or real keys!*
