# Add this to your Django app's views.py or create a new file

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import redis
from datetime import datetime

# Initialize Redis connection
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

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

    # POST - receive new tick
    try:
        if request.body:
            tick_data = json.loads(request.body)
        else:
            return JsonResponse({'status': 'error', 'message': 'No data provided'}, status=400)

        # Add timestamp if not present
        if 'timestamp' not in tick_data:
            tick_data['timestamp'] = datetime.now().isoformat()

        # Store in Redis stream
        redis_client.xadd('ticks', tick_data, maxlen=10000)

        # Also publish to channel for real-time subscribers
        redis_client.publish('tick_channel', json.dumps(tick_data))

        return JsonResponse({
            'status': 'success',
            'message': 'Tick stored',
            'data': tick_data
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Add to your urls.py:
# from django.urls import path
# from . import views  # or wherever you put the view
# 
# urlpatterns = [
#     path('api/ticks/', views.tick_ingestion, name='tick_ingestion'),
# ]
