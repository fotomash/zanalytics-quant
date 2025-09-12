FROM python:3.11-slim

WORKDIR /app

COPY services/vectorization_service/requirements.txt /app/requirements.txt
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the service into a subdirectory to keep it as a package
COPY services /app/services

# Run the service using module invocation to preserve package context
CMD ["python", "-m", "services.vectorization_service.main"]
