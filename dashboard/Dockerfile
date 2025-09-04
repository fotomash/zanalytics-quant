# --------------------------------------------------------------
# Zanalytics  –  Python 3.11  +  TA-Lib 0.6.4  +  all Python deps
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

# native lib
COPY --from=builder /usr/lib/libta_lib*.so* /usr/lib/
RUN ldconfig

# site-packages + entrypoints
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
ENV PYTHONPATH="/app"
COPY . .
RUN chmod +x scripts/startup.sh

# Streamlit/FastAPI etc. will set their own port; expose for local dev
EXPOSE 8501
CMD ["scripts/startup.sh"]