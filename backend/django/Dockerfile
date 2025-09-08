# backend/django/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=app.settings \
    DJANGO_LOG_DIR=/app/backend/django/logs \
    PYTHONPATH=/app/backend/django:/app:/app/components:/app/utils:/app/backend/django/app

# (Optional) run as non-root
ARG APP_USER=app
RUN adduser --disabled-password --gecos "" ${APP_USER}

WORKDIR /app

# 1) Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# 2) Copy your code
#    Django project is under backend/django/
COPY backend/django /app/backend/django
#    Shared modules at repo root (lowercase):
COPY components /app/components
COPY utils      /app/utils

# Ensure runtime log directory exists (matches settings.py LOG_DIR)
RUN mkdir -p /app/backend/django/logs /app/backend/django/staticfiles /app/logs /app/staticfiles \
    && touch /app/backend/django/logs/quant.log \
    && chown -R ${APP_USER}:${APP_USER} /app

# Make sure Python can import:
# - backend/django  (so `import app.settings` works if the package folder is /app/backend/django/app)
# - components and utils shared modules

USER ${APP_USER}

# Use the manage.py that lives under backend/django
CMD sh -lc '\
  mkdir -p "${DJANGO_LOG_DIR:-/app/logs}" && touch "${DJANGO_LOG_DIR:-/app/logs}/quant.log" ; \
  python /app/backend/django/manage.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} || true ; \
  exec gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 \
'
