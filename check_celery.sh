#!/bin/bash

echo "Checking Celery Configuration..."
echo "================================="
echo ""

# Check Django Celery configuration
echo "1. Django Celery Settings:"
docker-compose exec -T django python -c "
from django.conf import settings
print(f'CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}')
print(f'CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}')
" 2>/dev/null || echo "Could not read Django settings"

echo ""
echo "2. Celery Worker Status:"
docker-compose exec -T django celery -A zanalytics_quant inspect active 2>/dev/null || echo "Celery not responding"

echo ""
echo "3. Celery Beat Status:"
docker-compose exec -T django celery -A zanalytics_quant inspect scheduled 2>/dev/null || echo "No scheduled tasks"

echo ""
echo "4. Redis Keys:"
docker-compose exec -T redis redis-cli --raw KEYS "celery*" 2>/dev/null || echo "No Celery keys in Redis"
