FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG DJANGO_SECRET_KEY=dummy

WORKDIR /app

ENV PYTHONPATH="/app:/app/app"

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

RUN mkdir -p /app/logs && \
    mkdir -p /app/static && \
    chmod 777 /app/logs

CMD ["sh", "-c", "python manage.py collectstatic --noinput --settings=app.settings && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 app.wsgi:application"]