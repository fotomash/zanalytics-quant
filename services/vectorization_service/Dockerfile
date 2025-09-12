FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY requirements /app/requirements
COPY services/mcp2/requirements.txt /app/services/mcp2/requirements.txt
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the service into a subdirectory to keep it as a package
COPY services/vectorization_service /app/vectorization_service

# Run the service using module invocation to preserve package context
CMD ["python", "-m", "vectorization_service.main"]
