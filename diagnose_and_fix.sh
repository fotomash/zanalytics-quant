#!/bin/bash
# Zanalytics-Quant Diagnostic & Fix Script
# This script diagnoses and fixes common issues with tick data ingestion, 
# Celery, Django, and Grafana

set -e

echo "=========================================="
echo "Zanalytics-Quant System Diagnostic Tool"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service status
check_service() {
    local service=$1
    echo -n "Checking $service... "
    if docker-compose ps | grep -q "$service.*Up"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to check port availability
check_port() {
    local port=$1
    local service=$2
    echo -n "Checking port $port for $service... "
    if netstat -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✓ Open${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Not accessible${NC}"
        return 1
    fi
}

# Function to test API endpoint
test_endpoint() {
    local url=$1
    local name=$2
    echo -n "Testing $name endpoint... "
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✓ Accessible${NC}"
        return 0
    else
        echo -e "${RED}✗ Not accessible${NC}"
        return 1
    fi
}

echo ""
echo "1. CHECKING DOCKER SERVICES"
echo "----------------------------"

services=("traefik" "mt5" "postgres" "django" "redis" "celery" "celery-beat" "grafana" "prometheus")
failed_services=()

for service in "${services[@]}"; do
    if ! check_service "$service"; then
        failed_services+=("$service")
    fi
done

echo ""
echo "2. CHECKING NETWORK CONNECTIVITY"
echo "---------------------------------"

check_port 80 "Traefik HTTP"
check_port 443 "Traefik HTTPS"
check_port 8000 "Django"
check_port 6379 "Redis"
check_port 3000 "Grafana"
check_port 9090 "Prometheus"
check_port 5001 "MT5 API"

echo ""
echo "3. CHECKING API ENDPOINTS"
echo "-------------------------"

test_endpoint "http://localhost:8000/api/v1/ping/" "Django API"
test_endpoint "http://localhost:5001/health" "MT5 API"
test_endpoint "http://localhost:3000" "Grafana"
test_endpoint "http://localhost:9090" "Prometheus"

echo ""
echo "4. CHECKING REDIS CONNECTION"
echo "-----------------------------"

echo -n "Testing Redis connection... "
if docker exec redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✓ Connected${NC}"

    # Check Redis keys
    echo -n "Checking Redis keys... "
    key_count=$(docker exec redis redis-cli DBSIZE | awk '{print $2}')
    echo -e "${GREEN}Found $key_count keys${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
fi

echo ""
echo "5. CHECKING CELERY WORKERS"
echo "---------------------------"

echo -n "Checking Celery worker status... "
if docker logs celery 2>&1 | tail -20 | grep -q "ready"; then
    echo -e "${GREEN}✓ Worker ready${NC}"
else
    echo -e "${YELLOW}⚠ Worker may not be ready${NC}"
fi

echo -n "Checking Celery Beat status... "
if docker logs celery-beat 2>&1 | tail -20 | grep -q "beat: Starting"; then
    echo -e "${GREEN}✓ Beat scheduler running${NC}"
else
    echo -e "${YELLOW}⚠ Beat scheduler may have issues${NC}"
fi

echo ""
echo "6. CHECKING DATABASE CONNECTION"
echo "--------------------------------"

echo -n "Testing PostgreSQL connection... "
if docker exec postgres pg_isready -U admin | grep -q "accepting connections"; then
    echo -e "${GREEN}✓ Database ready${NC}"
else
    echo -e "${RED}✗ Database not ready${NC}"
fi

echo ""
echo "7. FIXING COMMON ISSUES"
echo "------------------------"

if [ ${#failed_services[@]} -gt 0 ]; then
    echo -e "${YELLOW}Found failed services: ${failed_services[*]}${NC}"
    echo "Attempting to fix..."

    # Fix 1: Restart failed services
    for service in "${failed_services[@]}"; do
        echo "Restarting $service..."
        docker-compose restart "$service" || docker-compose up -d "$service"
    done

    sleep 5
fi

# Fix 2: Django migrations
echo ""
echo "Running Django migrations..."
docker-compose exec -T django python manage.py migrate --noinput || echo "Migration failed or already up to date"

# Fix 3: Create Django superuser if not exists
echo "Ensuring Django superuser exists..."
docker-compose exec -T django python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created')
else:
    print('Superuser already exists')
" || echo "Could not check superuser"

# Fix 4: Clear Redis if needed
echo ""
read -p "Do you want to clear Redis cache? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker exec redis redis-cli FLUSHALL
    echo -e "${GREEN}Redis cache cleared${NC}"
fi

# Fix 5: Restart Celery workers
echo ""
echo "Restarting Celery workers..."
docker-compose restart celery celery-beat
sleep 5

echo ""
echo "8. GRAFANA DATASOURCE CONFIGURATION"
echo "------------------------------------"

# Check if Grafana datasources are configured
echo "Checking Grafana datasources..."
curl -s -u admin:admin http://localhost:3000/api/datasources | python3 -m json.tool || echo "Could not fetch datasources"

echo ""
echo "=========================================="
echo "DIAGNOSTIC COMPLETE"
echo "=========================================="

echo ""
echo "RECOMMENDED ACTIONS:"
echo "--------------------"

# Provide recommendations based on findings
if [ ${#failed_services[@]} -gt 0 ]; then
    echo "1. Some services are not running. Try:"
    echo "   docker-compose down"
    echo "   docker-compose up -d"
fi

echo "2. To view logs for debugging:"
echo "   docker-compose logs -f django    # Django logs"
echo "   docker-compose logs -f celery    # Celery logs"
echo "   docker-compose logs -f mt5       # MT5 API logs"

echo "3. To test tick data flow:"
echo "   curl http://localhost:5001/symbol_info_tick/EURUSD"

echo "4. Access services at:"
echo "   - Django Admin: http://localhost:8000/admin"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo "   - MT5 API Docs: http://localhost:5001/apidocs"

echo ""
echo "For persistent issues, check the .env file and ensure all required variables are set."
