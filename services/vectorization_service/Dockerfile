FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY requirements /app/requirements
COPY services/mcp2/requirements.txt /app/services/mcp2/requirements.txt
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/vectorization_service/ /app

CMD ["python", "main.py"]
