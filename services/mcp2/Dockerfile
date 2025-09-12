FROM python:3.11-slim

WORKDIR /app

# Copy all code (including requirements.txt) into image
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "services.mcp2.main:app", "--host", "0.0.0.0", "--port", "8002"]