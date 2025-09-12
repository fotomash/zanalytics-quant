FROM python:3.12-slim

WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY services/mcp2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (adjust path if needed)
COPY services/mcp2/ /app/

# Set environment variables (optional, can also be in compose)
ENV PYTHONPATH=/app

# Expose the port used by the healthcheck and Uvicorn
EXPOSE 8002

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]