from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import connections
import redis
import json

from .serializers import TickQuerySerializer, RiskEvalSerializer
from utils.data_query import get_ticks
from risk_enforcer import EnhancedRiskEnforcer
from .lib.http import SafeHTTP
from rest_framework.decorators import api_view


risk_enforcer = EnhancedRiskEnforcer()
redis_client = redis.Redis.from_url(
    getattr(settings, "REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
)


class LiveCheckView(APIView):
    def get(self, request):
        return Response({"status": "live"}, status=status.HTTP_200_OK)


class ReadyCheckView(APIView):
    def get(self, request):
        errors = []
        # Database
        try:
            conn = connections["default"]
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            errors.append(f"db: {e}")
        # Redis
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.ping()
        except Exception as e:
            errors.append(f"redis: {e}")
        # MT5 bridge
        mt5_base = getattr(settings, "MT5_URL", None)
        if mt5_base:
            try:
                mt5 = SafeHTTP(base=mt5_base)
                resp = mt5.get("/health")
                if "error" in resp:
                    errors.append(f"mt5: {resp['error']}")
            except Exception as e:
                errors.append(f"mt5: {e}")
        if errors:
            return Response({"status": "not ready", "errors": errors}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ready"}, status=status.HTTP_200_OK)


class TicksBufferView(APIView):
    def get(self, request):
        serializer = TickQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        if "start" in data and data["start"]:
            df = get_ticks(**data)
            records = df.tail(200).to_dict(orient="records")
            return Response({"rows": len(records), "data": records})
        else:
            symbol = data["symbol"]
            key = f"ticks:{symbol}:live"
            raw = redis_client.lrange(key, -200, -1)
            records = [json.loads(x) for x in raw]
            return Response({"symbol": symbol, "ticks": records, "source": "Redis"})


class RiskEvaluateView(APIView):
    def post(self, request):
        serializer = RiskEvalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = risk_enforcer.evaluate_trade_request(serializer.validated_data)
        return Response(result, status=status.HTTP_200_OK)


@api_view(["GET"])
def tick_buffer(request):
    """Function-based wrapper for legacy compatibility."""
    return TicksBufferView.as_view()(request._request)
