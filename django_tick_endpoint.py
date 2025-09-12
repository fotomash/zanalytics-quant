# Add this to your Django app's views.py or create a new file

import json
import os

import redis
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError

from schemas import TickPayload
from utils.mt5_kafka_producer import MT5KafkaProducer

# Initialize Redis connection
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# Initialize Kafka producer
kafka_producer = MT5KafkaProducer()

# Configuration for simple token auth and rate limiting
API_TOKEN = os.environ.get("TICK_API_TOKEN")
RATE_LIMIT = int(os.environ.get("TICK_RATE_LIMIT", "60"))

@csrf_exempt
@require_http_methods(["POST", "GET"])
def tick_ingestion(request):
    """
    Endpoint to receive tick data from MT5 or other sources
    """
    if request.method == "GET":
        # Return last tick for testing
        try:
            last_tick = redis_client.xrevrange('ticks', count=1)
            if last_tick:
                return JsonResponse({
                    'status': 'ok',
                    'last_tick': last_tick[0][1]
                })
            return JsonResponse({'status': 'ok', 'message': 'No ticks yet'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Authentication: require valid token or session
    auth_header = request.headers.get("Authorization")
    session_key = getattr(request, "session", None)
    session_key = getattr(session_key, "session_key", None)
    if API_TOKEN:
        expected = f"Token {API_TOKEN}"
        if auth_header != expected and not session_key:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

    # Basic rate limiting per token or IP
    identifier = auth_header or session_key or request.META.get('REMOTE_ADDR')
    rate_key = f"rate:{identifier}"
    try:
        current = redis_client.incr(rate_key)
        if current == 1:
            redis_client.expire(rate_key, 60)
        if current > RATE_LIMIT:
            return JsonResponse({'status': 'error', 'message': 'Rate limit exceeded'}, status=429)
    except Exception:
        pass  # if redis unavailable, skip limiting

    # POST - receive new tick
    try:
        if request.body:
            payload = json.loads(request.body)
        else:
            return JsonResponse({'status': 'error', 'message': 'No data provided'}, status=400)

        # Validate tick payload
        tick = TickPayload(**payload)
        tick_data = tick.model_dump()

        # Store in Redis stream for persistence/legacy consumers
        redis_client.xadd('ticks', tick_data, maxlen=10000)

        # Publish to Kafka for downstream processing
        kafka_producer.send_tick(tick_data)

        return JsonResponse({
            'status': 'success',
            'message': 'Tick stored',
            'data': tick_data
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.errors()}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Add to your urls.py:
# from django.urls import path
# from . import views  # or wherever you put the view
# 
# urlpatterns = [
#     path('api/ticks/', views.tick_ingestion, name='tick_ingestion'),
# ]
