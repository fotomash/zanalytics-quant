FROM python:3.11-slim

WORKDIR /app

# Install dependencies only for the Pulse API service
COPY services/pulse_api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy only the files needed to run the Pulse API
COPY services/pulse_api /app/services/pulse_api
COPY pulse_kernel.py pulse_config.yaml /app/

EXPOSE 8080

CMD ["uvicorn", "services.pulse_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
