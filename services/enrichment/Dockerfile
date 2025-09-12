FROM python:3.11-slim

# Show the Python version during build to confirm the interpreter is available
RUN python --version

WORKDIR /app

COPY services/enrichment/ /app/
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY utils/analysis_engines.py /app/utils/analysis_engines.py
COPY components /app/components
COPY schemas /app/schemas

ENV KAFKA_BROKER=kafka:9092 \
    RAW_MARKET_DATA_TOPIC=raw-market-data \
    ENRICHED_TOPIC=enriched-analysis-payloads

# Explicitly invoke python3 in case the environment does not provide a
# `python` shim.
CMD ["python3", "-u", "-m", "main"]
