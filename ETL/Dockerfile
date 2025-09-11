# Single-stage Dockerfile for running ETL workflows with Prefect
FROM python:3.11-slim

# Configure Prefect and Python paths
ENV PREFECT_HOME=/opt/prefect \
    PYTHONPATH=/opt/etl

WORKDIR /opt/etl

# Install Prefect for orchestration
RUN pip install --no-cache-dir prefect

# Copy ETL scripts into the image
COPY utils ./utils
COPY scripts ./scripts

# Start Prefect's Orion server by default
ENTRYPOINT ["prefect", "orion", "start"]
