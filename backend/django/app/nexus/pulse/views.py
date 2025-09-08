from __future__ import annotations

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .service import pulse_status
from .service import _load_minute_data
from .gates import structure_gate, liquidity_gate, imbalance_gate, risk_gate
from app.nexus.views import _redis_client


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


class PulseDetail(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol") or "XAUUSD"
        # Short-circuit cache for 3 seconds to reduce compute
        try:
            r = _redis_client()
            if r is not None:
                key = f"pulse:detail:{symbol}"
                raw = r.get(key)
                if raw:
                    import json as _json
                    return Response(_json.loads(raw))
        except Exception:
            pass
        data = _load_minute_data(symbol)
        try:
            m1 = data.get('M1')
            m15 = data.get('M15')
            struct = structure_gate(m1) if m1 is not None else {"passed": False}
            liq = liquidity_gate(m15) if m15 is not None else {"passed": False}
            imb = imbalance_gate(m1) if m1 is not None else {"passed": False, "entry_zone": [None, None]}
            rsk = risk_gate(imb, struct, symbol)
            payload = {"structure": struct, "liquidity": liq, "risk": rsk}
            try:
                r = _redis_client()
                if r is not None:
                    import json as _json
                    r.setex(f"pulse:detail:{symbol}", 3, _json.dumps(payload))
            except Exception:
                pass
            return Response(payload)
        except Exception:
            return Response({"structure": {"passed": False}, "liquidity": {"passed": False}})
