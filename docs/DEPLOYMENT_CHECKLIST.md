# Deployment Checklist (Django + Celery + `pulse-api` + Dashboard)

## Core services

- Django (port 8000 → 8010 mapped) — health: `/api/pulse/health`
- Redis (port 6379) — required for Celery + SSE pub/sub
- Celery worker — imports `app.celery`
- Celery beat — schedules SoD snapshot at 23:00
- `pulse-api` service (FastAPI) — `services/pulse_api/main.py`
- Dashboard (Streamlit) — depends on Django health

## docker compose

- Ensure `DJANGO_SECRET_KEY` only set once with default fallback
- Celery/Celery Beat:
  - `entrypoint`: `celery -A app worker|beat`
  - `PYTHONPATH` includes: `/app/backend/django:/app/agents:/app:/app/components:/app/utils:/app/backend`
  - mount `./agents:/app/agents`
- `pulse-api` service:
  - Command: `python -m uvicorn services.pulse_api.main:app --host 0.0.0.0 --port 8000`
  - Health: `/pulse/health`

## Build notes

- Server requirements use monolithic `requirements.txt` (no pandas-ta)
- Avoid VCS packages in server image where possible to prevent resolver issues
- If needed, install analytics libs (e.g., pandas-ta) in dashboard image or dev venv

## Verifications

- Django health: `GET /api/pulse/health`
- Risk endpoints: `/api/v1/account/risk`, `/api/v1/account/sod`
- Celery Beat logs show `snapshot_sod_equity` schedule
- Dashboard renders Macro/Pulse Pro without exceptions

