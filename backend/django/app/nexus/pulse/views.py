from __future__ import annotations

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .service import pulse_status


class PulseStatus(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol") or "XAUUSD"
        try:
            status = pulse_status(symbol)
        except Exception:
            # Hard fallback: empty lights rather than erroring
            status = {k: 0 for k in [
                'context', 'liquidity', 'structure', 'imbalance', 'risk', 'confluence'
            ]}
        return Response(status)

