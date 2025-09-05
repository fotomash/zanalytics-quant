#!/bin/bash

echo "=========================================="
echo "Zanalytics-Quant System Fix Script"
echo "=========================================="
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Fix docker-compose.override.yml version warning
echo "1. FIXING DOCKER-COMPOSE VERSION WARNING"
echo "-----------------------------------------"
if [ -f docker-compose.override.yml ]; then
    # Remove version line from override file
    sed -i.bak '/^version:/d' docker-compose.override.yml
    echo "✓ Removed obsolete version attribute from docker-compose.override.yml"
fi

# 2. Start Celery services
echo ""
echo "2. STARTING CELERY SERVICES"
echo "----------------------------"
docker-compose up -d celery celery-beat
sleep 5

# Check if Celery started
if docker-compose ps celery | grep -q "Up"; then
    echo "✓ Celery worker started successfully"
else
    echo "✗ Celery worker failed to start. Checking logs..."
    docker-compose logs --tail=50 celery
fi

if docker-compose ps celery-beat | grep -q "Up"; then
    echo "✓ Celery beat started successfully"
else
    echo "✗ Celery beat failed to start. Checking logs..."
    docker-compose logs --tail=50 celery-beat
fi

# 3. Fix Traefik routing (port 80 issue)
echo ""
echo "3. CHECKING TRAEFIK CONFIGURATION"
echo "----------------------------------"
# Check if Traefik is actually listening on the right ports
docker-compose exec -T traefik wget -q -O- http://localhost:80 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Traefik is responding on port 80 inside container"
else
    echo "⚠ Traefik may not be configured correctly"
fi

# Check Docker port mapping
echo "Docker port mappings for Traefik:"
docker port $(docker-compose ps -q traefik) 2>/dev/null || echo "No port mappings found"

# 4. Test MT5 tick data flow to Django
echo ""
echo "4. TESTING DATA FLOW: MT5 → DJANGO"
echo "-----------------------------------"
# Test if Django can receive tick data
DJANGO_URL="http://localhost:8000"
MT5_URL="http://localhost:5001"

# First check if Django is accessible
if curl -s -o /dev/null -w "%{http_code}" $DJANGO_URL/admin/ | grep -q "200\|301\|302"; then
    echo "✓ Django is accessible"

    # Test tick endpoint if it exists
    if curl -s -o /dev/null -w "%{http_code}" $DJANGO_URL/api/ticks/ | grep -q "200\|401\|403"; then
        echo "✓ Django tick API endpoint exists"
    else
        echo "⚠ Django tick API endpoint may not be configured"
    fi
else
    echo "✗ Django is not accessible on port 8000"
fi

# 5. Check Redis connectivity
echo ""
echo "5. TESTING REDIS CONNECTIVITY"
echo "------------------------------"
docker-compose exec -T redis redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Redis is responding to PING"

    # Check for tick data in Redis
    echo "Checking for tick data in Redis streams..."
    docker-compose exec -T redis redis-cli --raw XLEN ticks 2>/dev/null || echo "No 'ticks' stream found yet"
else
    echo "✗ Redis is not responding"
fi

# 6. Create tick ingestion test
echo ""
echo "6. TESTING TICK INGESTION PIPELINE"
echo "-----------------------------------"
# Test the complete pipeline
python3 - <<EOF
import requests
import json
import time

print("Testing MT5 tick fetch...")
try:
    # Get tick from MT5
    mt5_response = requests.get("http://localhost:5001/symbol_info_tick/EURUSD", timeout=5)
    if mt5_response.status_code == 200:
        tick_data = mt5_response.json()
        print(f"✓ Got tick from MT5: {tick_data}")

        # Try to send to Django (if endpoint exists)
        try:
            django_response = requests.post(
                "http://localhost:8000/api/ticks/",
                json=tick_data,
                timeout=5
            )
            if django_response.status_code in [200, 201]:
                print("✓ Tick sent to Django successfully")
            else:
                print(f"⚠ Django returned status {django_response.status_code}")
        except Exception as e:
            print(f"⚠ Could not send to Django: {e}")
    else:
        print(f"✗ MT5 returned status {mt5_response.status_code}")
except Exception as e:
    print(f"✗ Error testing pipeline: {e}")
EOF

# 7. Start tick-to-bar service if configured
echo ""
echo "7. CHECKING TICK-TO-BAR SERVICE"
echo "--------------------------------"
if docker-compose config --services | grep -q "tick-to-bar"; then
    docker-compose up -d tick-to-bar
    sleep 3
    if docker-compose ps tick-to-bar | grep -q "Up"; then
        echo "✓ Tick-to-bar service started"
    else
        echo "✗ Tick-to-bar service failed to start"
        docker-compose logs --tail=20 tick-to-bar
    fi
else
    echo "⚠ Tick-to-bar service not configured in docker-compose"
fi

# 8. Summary and recommendations
echo ""
echo "=========================================="
echo "SUMMARY & RECOMMENDATIONS"
echo "=========================================="
echo ""

# Count running services
RUNNING=$(docker-compose ps | grep "Up" | wc -l)
TOTAL=$(docker-compose config --services | wc -l)

echo "Services running: $RUNNING / $TOTAL"
echo ""

if [ $RUNNING -lt $TOTAL ]; then
    echo "⚠ Not all services are running. Check individual service logs:"
    echo "  docker-compose logs [service-name]"
    echo ""
fi

echo "Next steps:"
echo "1. If Celery is not starting, check Redis connection in Django settings"
echo "2. Ensure Django migrations are applied: docker-compose exec django python manage.py migrate"
echo "3. Create Django superuser if needed: docker-compose exec django python manage.py createsuperuser"
echo "4. Check Grafana at http://localhost:3000 (admin/admin)"
echo "5. Monitor logs: docker-compose logs -f django celery mt5"
echo ""
echo "To test the complete tick flow:"
echo "  python test_tick_flow.py"
