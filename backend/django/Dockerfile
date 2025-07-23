# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Build argument to provide a secret key for collectstatic
ARG DJANGO_SECRET_KEY=dummy

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

RUN mkdir -p /app/logs && \
    mkdir -p /app/static && \
    chmod 777 /app/logs

# Temporary secret key needed for collectstatic during build
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
RUN python manage.py collectstatic --noinput
ENV DJANGO_SECRET_KEY=

# Run the Django development server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "app.wsgi:application"]
