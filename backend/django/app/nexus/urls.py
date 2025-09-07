from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.routers import DefaultRouter
from .views import (
    TradeViewSet,
    SendMarketOrderView,
    ModifySLTPView,
    ProtectPositionView,
    TickViewSet,
    BarViewSet,
    SymbolListView,
    TimeframeListView,
    DashboardDataView,
    JournalEntryView,
)

# --- Minimal, dependency-free Pulse endpoints (stubs) ---
def pulse_health(request):
    return JsonResponse({
        "status": "ok",
        "service": "django",
        "ts": timezone.now().isoformat()
    })


def pulse_risk_summary(request):
    """Proxy to real Pulse risk summary if available; else degrade gracefully."""
    try:
        # Import here to avoid import timing/cycles
        from pulse_api.views import risk_summary as _real_risk_summary
        return _real_risk_summary(request)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "risk_left": None,
            "trades_left": None,
            "as_of": timezone.now().isoformat()
        }, status=500)


router = DefaultRouter()
router.register(r'trades', TradeViewSet)
router.register(r'ticks', TickViewSet)
router.register(r'bars', BarViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Minimal pulse endpoints under /api/v1/
    path('pulse/health', pulse_health, name='pulse-health-v1'),
    path('pulse/risk/summary', pulse_risk_summary, name='pulse-risk-summary-v1'),
    path('send_market_order/', SendMarketOrderView.as_view(), name='send_market_order'),
    path('modify_sl_tp/', ModifySLTPView.as_view(), name='modify_sl_tp'),
    path('trades/protect/', ProtectPositionView.as_view(), name='protect_trade'),
    path('symbols/', SymbolListView.as_view(), name='symbols'),
    path('timeframes/', TimeframeListView.as_view(), name='timeframes'),
    path('dashboard-data/', DashboardDataView.as_view(), name='dashboard-data'),
    path('journal/', JournalEntryView.as_view(), name='journal'),
]
