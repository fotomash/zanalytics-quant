"""
Production-ready Django API views for Pulse system
"""
import json
import time
import os
from datetime import datetime
import logging
import pandas as pd
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
import redis
from .strategy_match_engine import match_strategy
from .situation_builder import build_situation
from agents.analyzers import compute_confluence

# Import your risk enforcer (prefer app-local, then external fallback)
RISK_ENFORCER_AVAILABLE = False
EnhancedRiskEnforcer = None  # type: ignore
try:
    from app.risk_enforcer import EnhancedRiskEnforcer  # app-local
    RISK_ENFORCER_AVAILABLE = True
except Exception:
    try:
        from risk_enforcer import EnhancedRiskEnforcer  # external / root
        RISK_ENFORCER_AVAILABLE = True
    except Exception:
        EnhancedRiskEnforcer = None  # type: ignore

logger = logging.getLogger(__name__)

# Initialize risk enforcer
if RISK_ENFORCER_AVAILABLE:
    risk_enforcer = EnhancedRiskEnforcer()
else:
    risk_enforcer = None


# Redis connection used by API endpoints
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
)

@csrf_exempt
@require_http_methods(["GET"])
def pulse_health(request):
    """Health check endpoint with latency measurement"""
    start_time = time.time()
    
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "lag_ms": int((time.time() - start_time) * 1000),
            "version": "v11.5.1",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "risk_enforcer": "available" if RISK_ENFORCER_AVAILABLE else "unavailable",
                "redis": "checking",
                "mt5": "checking"
            }
        }
        
        # Test risk enforcer
        if risk_enforcer:
            try:
                risk_enforcer.get_risk_status()
                health_status["components"]["risk_enforcer"] = "healthy"
            except Exception:
                health_status["components"]["risk_enforcer"] = "error"
        
        return JsonResponse(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def score_peek(request):
    """Get current confluence score with explainable reasons"""
    try:
        payload = json.loads(request.body or "{}")
        bars = payload.get("bars")
        if not bars:
            return JsonResponse(
                {
                    "error": "'bars' field required",
                    "timestamp": datetime.now().isoformat(),
                },
                status=400,
            )

        df = pd.DataFrame(bars)
        result = compute_confluence(df)
        result["timestamp"] = datetime.now().isoformat()
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        logger.error(f"Score peek error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def score_post(request):
    """Compatibility wrapper for legacy /api/pulse/score endpoint."""
    return score_peek(request)


@api_view(["GET"])
def tick_buffer(request):
    """Fetch the last ticks for a symbol from Redis."""
    symbol = request.GET.get("symbol", "EURUSD").upper()
    key = f"ticks:{symbol}:live"
    raw = redis_client.lrange(key, -5, -1)
    ticks = [json.loads(x) for x in raw]
    return Response({"symbol": symbol, "ticks": ticks, "source": "Redis"})

@csrf_exempt
@require_http_methods(["POST"])
def risk_check(request):
    """Pre-trade risk evaluation"""
    try:
        payload = json.loads(request.body or "{}")
        
        if not risk_enforcer:
            return JsonResponse({
                "decision": "block",
                "reasons": ["Risk enforcer unavailable"],
                "timestamp": datetime.now().isoformat()
            })
        
        # Evaluate trade request
        result = risk_enforcer.evaluate_trade_request(payload)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        logger.error(f"Risk check error: {e}")
        return JsonResponse({
            "decision": "block",
            "reasons": [f"System error: {str(e)}"],
            "timestamp": datetime.now().isoformat()
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def risk_summary(request):
    """Current risk status for dashboard tiles"""
    try:
        if not risk_enforcer:
            return JsonResponse({
                "risk_left": 100.0,
                "trades_left": 5,
                "status": "Unknown",
                "warnings": ["Risk enforcer unavailable"],
                "daily_risk_used": 0.0,
                "timestamp": datetime.now().isoformat()
            })
        
        risk_status = risk_enforcer.get_risk_status()
        
        # Format for dashboard
        payload = {
            "risk_left": risk_status.get("risk_remaining_pct", 0),
            "trades_left": risk_status.get("trades_remaining", 0),
            "status": risk_status.get("status", "Unknown"),
            "warnings": risk_status.get("warnings", []),
            "daily_risk_used": risk_status.get("daily_risk_used", 0),
            "timestamp": datetime.now().isoformat()
        }
        # Publish to Redis so UI can read without calling API
        try:
            from app.utils.pulse_bus import publish_risk_summary
            publish_risk_summary(payload)
        except Exception:
            pass
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"Risk summary error: {e}")
        return JsonResponse({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def risk_update(request):
    """Update live daily stats for the risk enforcer (PnL, trades count, streak).

    Body JSON fields (all optional):
      - total_pnl: float (USD)
      - trades_count: int
      - consecutive_losses: int
      - cooling_until: ISO8601 string (optional)
    Returns the current risk_summary payload and publishes to Redis.
    """
    try:
        if not risk_enforcer:
            return JsonResponse({
                "error": "Risk enforcer unavailable",
                "timestamp": datetime.now().isoformat()
            }, status=503)
        data = json.loads(request.body or "{}")
        # Update core stats if present
        ds = getattr(risk_enforcer, 'core', None).daily_stats if hasattr(risk_enforcer, 'core') else None
        if ds is None:
            return JsonResponse({"error": "Enforcer state not available"}, status=500)
        if 'total_pnl' in data:
            try:
                ds['total_pnl'] = float(data['total_pnl'])
            except Exception:
                pass
        if 'trades_count' in data:
            try:
                ds['trades_count'] = int(data['trades_count'])
            except Exception:
                pass
        if 'consecutive_losses' in data:
            try:
                ds['consecutive_losses'] = int(data['consecutive_losses'])
            except Exception:
                pass
        if 'cooling_until' in data:
            try:
                # accept ISO; store raw string or parsed datetime depending on enforcer
                ds['cooling_until'] = data['cooling_until']
            except Exception:
                pass

        # Build current summary via enforcer
        status_payload = risk_enforcer.get_risk_status()
        payload = {
            "risk_left": status_payload.get("risk_remaining_pct", 0),
            "trades_left": status_payload.get("trades_remaining", 0),
            "status": status_payload.get("status", "Unknown"),
            "warnings": status_payload.get("warnings", []),
            "daily_risk_used": status_payload.get("daily_risk_used", 0),
            "timestamp": datetime.now().isoformat()
        }
        # Publish to Redis for UI
        try:
            from app.utils.pulse_bus import publish_risk_summary
            publish_risk_summary(payload)
        except Exception:
            pass
        return JsonResponse(payload)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        logger.error(f"Risk update error: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def signals_top(request):
    """Top trading opportunities with explanations"""
    try:
        n = int(request.GET.get("n", 3))
        
        # Mock signals for now - replace with actual implementation
        signals = [
            {
                "symbol": "EURUSD",
                "score": 85,
                "rr": 2.1,
                "bias": "Bull",
                "sl": "1.0940",
                "tp": "1.1060",
                "reasons": ["SMC Break of Structure", "Volume Confirmation"]
            },
            {
                "symbol": "GBPUSD",
                "score": 78,
                "rr": 1.9,
                "bias": "Bull",
                "sl": "1.2660",
                "tp": "1.2790",
                "reasons": ["Wyckoff Accumulation Phase"]
            },
            {
                "symbol": "XAUUSD",
                "score": 72,
                "rr": 2.0,
                "bias": "Bear",
                "sl": "2392",
                "tp": "2350",
                "reasons": ["Liquidity Sweep Detected"]
            }
        ]
        
        return JsonResponse(signals[:n], safe=False)
        
    except ValueError:
        return HttpResponseBadRequest("Invalid parameter 'n'")
    except Exception as e:
        logger.error(f"Signals top error: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def adapter_status(request):
    """MIDAS adapter health check"""
    try:
        # Mock adapter status - replace with actual implementation
        return JsonResponse({
            "status": "up",
            "fps": 10,
            "lag_ms": 120,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Adapter status error: {e}")
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def pulse_journal(request):
    """Recent risk decisions from journal"""
    try:
        n = int(request.GET.get("n", 20))
        
        # Mock journal entries - replace with actual implementation
        entries = [
            {
                "timestamp": datetime.now().isoformat(),
                "symbol": "EURUSD",
                "decision": "allow",
                "reasons": ["Daily loss within limits", "Trade frequency OK"],
                "rr": 2.0
            }
        ]
        
        return JsonResponse(entries[:n], safe=False)

    except ValueError:
        return HttpResponseBadRequest("Invalid parameter 'n'")
    except Exception as e:
        logger.error(f"Journal error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def strategy_match(request):
    """Match current market situation to configured strategies."""
    try:
        payload = json.loads(request.body or "{}")
        symbol = payload.get("symbol") or request.GET.get("symbol", "XAUUSD")
        situation = build_situation(symbol)
        result = match_strategy(situation, confidence_threshold=0.6)
        result["timestamp"] = datetime.now().isoformat()
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
