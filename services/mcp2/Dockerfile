FROM python:3.12-slim
WORKDIR /app
# Use repo-root context; copy service-specific requirements explicitly
COPY services/mcp2/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Copy entire repo so imports like backend.mcp.schemas resolve
COPY . .
ENV PYTHONPATH=/app
RUN useradd -m appuser
USER appuser
EXPOSE 8002
ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
x§