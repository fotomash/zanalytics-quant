FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY services/pulse_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

# Copy application code
COPY services/pulse_api /app/services/pulse_api
COPY pulse_kernel.py pulse_config.yaml /app/

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "services.pulse_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
