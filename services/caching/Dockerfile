FROM python:3.11-slim

WORKDIR /app

COPY services/caching/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/caching/main.py /app/main.py

ENV KAFKA_BROKERS=kafka:9092 \
    KAFKA_GROUP=caching-service \
    KAFKA_TOPIC=enriched-analysis-payloads \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    LATEST_PAYLOAD_TTL=3600 \
    ACTIVE_FVG_TTL=3600 \
    BEHAVIORAL_SCORE_TTL=3600

CMD ["python", "-u", "main.py"]
