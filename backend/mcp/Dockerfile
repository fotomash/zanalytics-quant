FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy FastAPI app sources
COPY mcp_server.py mt5_adapter.py auth.py models.py schemas.py __init__.py openai-actions.yaml .
# Copy shared utils used by the app (e.g., time_utils)
COPY utils /app/utils/
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8001"]
