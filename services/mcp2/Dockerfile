FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

ENV PYTHONPATH=/app
RUN useradd -m appuser
USER appuser
EXPOSE 8002
ENTRYPOINT ["uvicorn", "services.mcp2.app:app", "--host", "0.0.0.0", "--port", "8002"]
