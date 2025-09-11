FROM python:3.11-slim

WORKDIR /app

COPY services/overseer/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "-m", "services.overseer.main"]
