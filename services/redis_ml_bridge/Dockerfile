FROM python:3.11-slim
WORKDIR /app
COPY services/redis_ml_bridge.py services/redis_ml_bridge.py
RUN pip install --no-cache-dir redis
CMD ["python", "services/redis_ml_bridge.py"]
