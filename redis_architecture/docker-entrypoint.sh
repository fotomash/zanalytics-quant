#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_HOST -p 5432 -U $POSTGRES_USER
do
  echo "Waiting for database connection..."
  sleep 2
done

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
