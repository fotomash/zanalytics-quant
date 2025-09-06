"""
Production-ready Django API views for Pulse system
"""
import json
import time
from datetime import datetime
import logging
import pandas as pd
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .strategy_match_engine import match_strategy
from .situation_builder import build_situation
from agents.analyzers import compute_confluence

# Import your risk enforcer
try:
    from risk_enforcer import EnhancedRiskEnforcer
    RISK_ENFORCER_AVAILABLE = True
except ImportError:
    RISK_ENFORCER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Initialize risk enforcer
if RISK_ENFORCER_AVAILABLE:
    risk_enforcer = EnhancedRiskEnforcer()
else:
    risk_enforcer = None

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
        bars = payload.get("bars", [])
        if not bars:
            return HttpResponseBadRequest("'bars' field required")

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
        return JsonResponse({
            "risk_left": risk_status.get("risk_remaining_pct", 0),
            "trades_left": risk_status.get("trades_remaining", 0),
            "status": risk_status.get("status", "Unknown"),
            "warnings": risk_status.get("warnings", []),
            "daily_risk_used": risk_status.get("daily_risk_used", 0),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Risk summary error: {e}")
        return JsonResponse({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)

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
