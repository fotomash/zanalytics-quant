FROM python:3.11-slim
WORKDIR /app
COPY services/persistence/ services/persistence/
RUN pip install --no-cache-dir psycopg2-binary confluent-kafka prometheus-client
CMD ["python", "services/persistence/consumer.py"]
