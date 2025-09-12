FROM python:3.11-slim

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

CMD ["python", "-u", "-m", "worker"]
