FROM python:3.11-slim
WORKDIR /app
COPY services/pulse_bot/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
