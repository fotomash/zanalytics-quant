from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.routers import DefaultRouter
from .views import (
    TradeViewSet,
    SendMarketOrderView,
    ModifySLTPView,
    ProtectPositionView,
    DisciplineSummaryView,
    PositionsPartialCloseView,
    TickViewSet,
    BarViewSet,
    SymbolListView,
    TimeframeListView,
    DashboardDataView,
    JournalEntryView,
    FeedBalanceView,
    FeedEquityView,
    FeedTradeView,
    FeedBehaviorView,
    ProfitHorizonView,
    MirrorStateView,
    MarketMiniView,
    MarketFetchView,
    MarketNewsPublisherView,
    PositionsProxyView,
    AccountInfoView,
    JournalAppendView,
    JournalRecentView,
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
    # Non-router actions first to avoid router capture (e.g., 'trades/<pk>')
    path('protect/position/', ProtectPositionView.as_view(), name='protect_position'),
    # Legacy alias kept before router to avoid capture by 'trades/<pk>'
    path('trades/protect/', ProtectPositionView.as_view(), name='protect_trade'),

    # Router-backed resources
    path('', include(router.urls)),

    # Minimal pulse endpoints under /api/v1/
    path('pulse/health', pulse_health, name='pulse-health-v1'),
    path('pulse/risk/summary', pulse_risk_summary, name='pulse-risk-summary-v1'),
    path('send_market_order/', SendMarketOrderView.as_view(), name='send_market_order'),
    path('modify_sl_tp/', ModifySLTPView.as_view(), name='modify_sl_tp'),
    path('symbols/', SymbolListView.as_view(), name='symbols'),
    path('timeframes/', TimeframeListView.as_view(), name='timeframes'),
    path('dashboard-data/', DashboardDataView.as_view(), name='dashboard-data'),
    path('discipline/summary', DisciplineSummaryView.as_view(), name='discipline-summary'),
    path('positions/partial_close', PositionsPartialCloseView.as_view(), name='positions-partial-close'),
    path('journal/', JournalEntryView.as_view(), name='journal'),
    # Feeds (spec)
    path('feed/balance', FeedBalanceView.as_view(), name='feed-balance'),
    path('feed/equity', FeedEquityView.as_view(), name='feed-equity'),
    path('feed/trade', FeedTradeView.as_view(), name='feed-trade'),
    path('feed/behavior', FeedBehaviorView.as_view(), name='feed-behavior'),
    path('profit-horizon', ProfitHorizonView.as_view(), name='profit-horizon'),
    path('mirror/state', MirrorStateView.as_view(), name='mirror-state'),
    path('market/mini', MarketMiniView.as_view(), name='market-mini'),
    path('market/fetch', MarketFetchView.as_view(), name='market-fetch'),
    path('market/news/next', MarketNewsPublisherView.as_view(), name='market-news-next'),
    path('account/positions', PositionsProxyView.as_view(), name='account-positions'),
    path('positions/open', PositionsProxyView.as_view(), name='positions-open'),
    path('account/info', AccountInfoView.as_view(), name='account-info'),
    path('journal/append', JournalAppendView.as_view(), name='journal-append'),
    path('journal/recent', JournalRecentView.as_view(), name='journal-recent'),
]
