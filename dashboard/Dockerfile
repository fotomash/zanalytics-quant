# --------------------------------------------------------------
# Zanalytics Dashboard  –  Python 3.11  +  TA-Lib 0.6.4  + deps
# --------------------------------------------------------------
# syntax=docker/dockerfile:1

############################
# 1️⃣  Builder  – TA-Lib + wheels
############################
FROM python:3.11-slim AS builder
ARG TA_VERSION=0.6.4

# OS build tools
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates pkg-config libtool && \
    rm -rf /var/lib/apt/lists/*

# Build native TA-Lib (parallel ok in 0.6.4)
RUN wget -q "https://github.com/ta-lib/ta-lib/releases/download/v${TA_VERSION}/ta-lib-${TA_VERSION}-src.tar.gz" \
        -O /tmp/ta-lib.tar.gz && \
    mkdir /tmp/ta-lib && \
    tar -xzf /tmp/ta-lib.tar.gz -C /tmp/ta-lib --strip-components=1 && \
    cd /tmp/ta-lib && \
        ./configure --prefix=/usr --libdir=/usr/lib && \
        make -j"$(nproc)" && make install && \
    strip -s /usr/lib/libta_lib*.so* || true && \
    rm -rf /tmp/*

# Python deps (wrapper builds here)
WORKDIR /wheels
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

############################
# 2️⃣  Runtime  – slim image
############################
FROM python:3.11-slim

# Add a non-root user for safety
ARG APP_USER=app
RUN adduser --disabled-password --gecos "" ${APP_USER}

# Native lib from builder
COPY --from=builder /usr/lib/libta_lib*.so* /usr/lib/
RUN ldconfig

# site-packages + entrypoints from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Handy CLI tools for debugging inside the container
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=app.settings \
    DJANGO_LOG_DIR=/app/backend/django/logs \
    PYTHONPATH=/app/backend/django:/app:/app/components:/app/utils \
    # Default MT5 API base; can be overridden via env or .env \
    MT5_API_BASE=http://mt5:5001 \
    PULSE_API_BASE=http://django:8000

# Working dir will be the repo-mounted dashboard folder
WORKDIR /app/dashboard

# Note: code is volume-mounted via docker-compose, so we don't copy sources here.

# Make sure Python can see shared modules that are mounted via volumes in docker-compose:
#   - ./components -> /app/components
#   - ./utils      -> /app/utils
ENV PYTHONPATH="/app:/app/dashboard:/app/components:/app/utils"

# Ensure runtime log directory exists (create as root, then drop back to ${APP_USER})
USER root
RUN install -d -m 0755 -o ${APP_USER} -g ${APP_USER} /app/logs /app/staticfiles \
    && touch /app/logs/quant.log
USER ${APP_USER}

EXPOSE 8501
# This CMD is a fallback; docker-compose can override with `command:`.
CMD sh -lc '\
  mkdir -p "${DJANGO_LOG_DIR:-/app/logs}" && touch "${DJANGO_LOG_DIR:-/app/logs}/quant.log" ; \
  python /app/backend/django/manage.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} || true ; \
  exec gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 \
'