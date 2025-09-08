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
        # Optional weight overrides via query params w_context, w_liquidity, ...
        weights = {}
        for k in ("context", "liquidity", "structure", "imbalance", "risk"):
            v = request.query_params.get(f"w_{k}")
            try:
                if v is not None:
                    weights[k] = float(v)
            except Exception:
                pass
        thr = request.query_params.get("threshold") or request.query_params.get("thr")
        try:
            thr_val = float(thr) if thr is not None else None
        except Exception:
            thr_val = None
        try:
            status = pulse_status(symbol, weights=weights or None, threshold=thr_val)
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
            # Include confluence summary (same weights/threshold as status endpoint defaults)
            try:
                from .service import _resolve_weights
                from .confluence_score_engine import compute_confluence_score
                w = _resolve_weights(None, symbol=symbol)
                score, reasons = compute_confluence_score(
                    {"context": {"passed": False}, "liquidity": liq, "structure": struct, "imbalance": imb, "risk": rsk},
                    w,
                )
                conf = {"confidence": score, "passed": bool(reasons.get("score_passed"))}
            except Exception:
                conf = {"confidence": 0.0, "passed": False}
            payload = {"structure": struct, "liquidity": liq, "risk": rsk, "confluence": conf}
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


class PulseWeights(views.APIView):
    """Persist and retrieve confluence weights + threshold via Redis.

    GET  -> {"weights": {..}, "threshold": float}
    POST -> accepts JSON with same structure; stores with TTL (optional)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            r = _redis_client()
            symbol = request.query_params.get("symbol") or None
            # Prefer symbol-specific; fallback to global
            key = f"pulse:conf_weights:{symbol}" if symbol else "pulse:conf_weights"
            if r is not None:
                raw = r.get(key)
                if (not raw) and symbol:
                    raw = r.get("pulse:conf_weights")
                if raw:
                    import json as _json
                    return Response(_json.loads(raw))
        except Exception:
            pass
        # Default response if nothing stored
        return Response({
            "weights": {"context": 0.2, "liquidity": 0.2, "structure": 0.25, "imbalance": 0.15, "risk": 0.2},
            "threshold": 0.6,
        })

    def post(self, request):
        try:
            data = request.data or {}
            symbol = data.get("symbol") or None
            weights = data.get("weights") or {}
            threshold = float(data.get("threshold")) if data.get("threshold") is not None else 0.6
            if not isinstance(weights, dict):
                return Response({"error": "weights must be an object"}, status=400)
            # Sanitize
            clean = {k: float(v) for k, v in weights.items() if k in {"context", "liquidity", "structure", "imbalance", "risk"} and isinstance(v, (int, float))}
            payload = {"weights": clean, "threshold": float(threshold)}
            r = _redis_client()
            if r is not None:
                import json as _json
                if symbol:
                    r.set(f"pulse:conf_weights:{symbol}", _json.dumps(payload))
                else:
                    r.set("pulse:conf_weights", _json.dumps(payload))
            return Response({"ok": True, **payload})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class PulseGateHits(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        symbol = request.query_params.get("symbol")
        try:
            limit = int(request.query_params.get("limit") or 100)
        except Exception:
            limit = 100
        try:
            r = _redis_client()
            items = []
            if r is not None:
                raw_list = r.lrange("pulse:gate_hits", -limit, -1) or []
                import json as _json
                for raw in reversed(raw_list):
                    try:
                        obj = _json.loads(raw)
                        if symbol and obj.get("symbol") != symbol:
                            continue
                        items.append(obj)
                    except Exception:
                        continue
            return Response({"items": items})
        except Exception as e:
            return Response({"items": [], "error": str(e)}, status=500)
