FROM python:3.11-slim
WORKDIR /app
COPY requirements.ml.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY .. /app
CMD ["python"]
