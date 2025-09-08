# Start‑of‑Day (SoD) Equity Snapshot

This document explains how SoD equity is captured daily and where it is surfaced.

## Overview

- Snapshot time: 23:00 (server timezone)
- Storage: Redis key `sod_equity:YYYYMMDD` (value is equity in USD)
- Producer: Celery beat task `nexus.tasks.snapshot_sod_equity`
- Consumers:
  - `GET /api/v1/account/risk` → keys: `sod_equity`, `prev_close_equity`
  - `GET /api/v1/account/sod?date=YYYY-MM-DD` → returns specific snapshot
  - Streamlit UIs (Macro, Pulse Pro, Pulse page 04) render SoD/Prev Close

## Files

- Task: `backend/django/app/nexus/tasks.py` → `snapshot_sod_equity`
- Schedule: `backend/django/app/settings.py` → `CELERY_BEAT_SCHEDULE['snapshot-sod-equity-2300']`
- Risk API: `backend/django/app/nexus/views.py` → `AccountRiskView`
- SoD API: `backend/django/app/nexus/views.py` → `AccountSoDView`

## Timezone

- The beat schedule uses `CELERY_TIMEZONE` (defaults to Django `TIME_ZONE`).
- Set `CELERY_TZ=Europe/London` in env to align 23:00 UK time.

## Validation

1. Confirm beat schedule:
   - `docker compose logs -f celery-beat` (look for `snapshot_sod_equity`)
2. Manual run (optional):
   - `docker compose exec django python -c "from app.nexus.tasks import snapshot_sod_equity as t; print(t.delay())"`
3. Inspect Redis:
   - `docker compose exec redis redis-cli GET sod_equity:$(date -d '+1 day' +%Y%m%d)`
4. API:
   - `GET /api/v1/account/risk` → includes `sod_equity`, `prev_close_equity`
   - `GET /api/v1/account/sod?date=YYYY-MM-DD`

