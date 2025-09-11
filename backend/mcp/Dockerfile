FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp_server.py mt5_adapter.py auth.py models.py openai-actions.yaml .
COPY utils /app/utils/
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8001"]
