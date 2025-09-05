FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore

ARG DJANGO_SECRET_KEY=dummy

# Work in project root
WORKDIR /app

# Make sure shared modules are importable across Django and Celery
# (cover both camel-case and lower-case just in case)
ENV PYTHONPATH="/app:/app/Components:/app/Utils:/app/backend:/app/components:/app/utils"

# Install dependencies from the repo root
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy application code
# Django app (contains manage.py)
COPY backend/django /app/backend/django
# Shared modules kept at repo root
COPY components /app/components
COPY utils /app/utils

# Ensure packages are importable even if these folders didn’t contain __init__.py
RUN mkdir -p /app/components /app/utils \
 && find /app/components -maxdepth 1 -type d -exec sh -lc 'touch "$1"/__init__.py' _ {} \; \
 && find /app/utils -maxdepth 1 -type d -exec sh -lc 'touch "$1"/__init__.py' _ {} \; \
 && mkdir -p /app/logs /app/static /app/backend/django/logs \
 && chmod -R 777 /app/logs /app/backend/django/logs

# Run from the Django folder so manage.py is on CWD
WORKDIR /app/backend/django

# Collect static and launch gunicorn (DJANGO_SETTINGS_MODULE supplied by env/compose)
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 app.wsgi:application"]