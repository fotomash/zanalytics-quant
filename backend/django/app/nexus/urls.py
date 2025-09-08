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
    EquitySeriesView,
    FeedTradeView,
    FeedBehaviorView,
    ProfitHorizonView,
    TradeHistoryView,
    MirrorStateView,
    MarketMiniView,
    MarketFetchView,
    MarketNewsPublisherView,
    PositionsProxyView,
    AccountInfoView,
    JournalAppendView,
    JournalRecentView,
    AccountRiskView,
    AccountSoDView,
    OrderMarketProxyView,
    OrderModifyProxyView,
    OrderCloseProxyView,
    DisciplineEventsView,
    DisciplineEventAppendView,
    MarketSymbolsView,
    MarketCalendarNextView,
    MarketRegimeView,
    FeedsStreamView,
    BehavioralPatternsView,
    BehaviorEventsTodayView,
    EquityTodayView,
    TradesRecentView,
    ActionsQueryView,
    ActionsMutateView,
    ActionsSpecView,
    JournalEntryPostView,
    SessionSetFocusView,
    PositionProtectOptionsView,
    UserPrefsView,
    StateSnapshotView,
)
from .views_positions import (
    PositionsCloseView,
    PositionsModifyView,
    PositionsHedgeView,
)
from .playbook_stub_views import (
    PlaybookSessionInit,
    LiquidityMapView,
    PriorityItemsView,
    ExplainSignalView,
    DailySummaryView,
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
    path('feed/equity/series', EquitySeriesView.as_view(), name='feed-equity-series'),
    path('equity/today', EquityTodayView.as_view(), name='equity-today'),
    path('feed/trade', FeedTradeView.as_view(), name='feed-trade'),
    path('feed/behavior', FeedBehaviorView.as_view(), name='feed-behavior'),
    path('profit-horizon', ProfitHorizonView.as_view(), name='profit-horizon'),
    path('trades/history', TradeHistoryView.as_view(), name='trades-history'),
    path('trades/recent', TradesRecentView.as_view(), name='trades-recent'),
    path('mirror/state', MirrorStateView.as_view(), name='mirror-state'),
    path('market/mini', MarketMiniView.as_view(), name='market-mini'),
    path('market/fetch', MarketFetchView.as_view(), name='market-fetch'),
    path('market/news/next', MarketNewsPublisherView.as_view(), name='market-news-next'),
    path('account/positions', PositionsProxyView.as_view(), name='account-positions'),
    # Convenience alias: open a position via orders/market
    path('positions/open', OrderMarketProxyView.as_view(), name='positions-open'),
    # LLM-friendly aliases
    path('positions/close', PositionsCloseView.as_view(), name='positions-close'),
    path('positions/modify', PositionsModifyView.as_view(), name='positions-modify'),
    path('positions/hedge', PositionsHedgeView.as_view(), name='positions-hedge'),
    path('account/info', AccountInfoView.as_view(), name='account-info'),
    path('journal/append', JournalAppendView.as_view(), name='journal-append'),
    path('journal/recent', JournalRecentView.as_view(), name='journal-recent'),
    path('account/risk', AccountRiskView.as_view(), name='account-risk'),
    path('account/sod', AccountSoDView.as_view(), name='account-sod'),
    path('orders/market', OrderMarketProxyView.as_view(), name='orders-market'),
    path('orders/modify', OrderModifyProxyView.as_view(), name='orders-modify'),
    path('orders/close', OrderCloseProxyView.as_view(), name='orders-close'),
    path('discipline/events', DisciplineEventsView.as_view(), name='discipline-events'),
    path('behavior/events/today', BehaviorEventsTodayView.as_view(), name='behavior-events-today'),
    path('discipline/event', DisciplineEventAppendView.as_view(), name='discipline-event'),
    path('market/symbols', MarketSymbolsView.as_view(), name='market-symbols'),
    path('market/calendar/next', MarketCalendarNextView.as_view(), name='market-calendar-next'),
    path('market/regime', MarketRegimeView.as_view(), name='market-regime'),
    path('feeds/stream', FeedsStreamView.as_view(), name='feeds-stream'),
    path('behavioral/patterns', BehavioralPatternsView.as_view(), name='behavioral-patterns'),
    path('journal/entry', JournalEntryPostView.as_view(), name='journal-entry'),
    path('session/set_focus', SessionSetFocusView.as_view(), name='session-set-focus'),
    path('positions/<int:ticket>/protect', PositionProtectOptionsView.as_view(), name='position-protect-options'),
    # Include pulse module endpoints
    path('', include('app.nexus.pulse.urls')),
    # User prefs (unauthenticated, minimal)
    path('user/prefs', UserPrefsView.as_view(), name='user-prefs'),
    # Playbook stubs
    path('playbook/session-init', PlaybookSessionInit.as_view(), name='playbook-session-init'),
    path('liquidity/map', LiquidityMapView.as_view(), name='liquidity-map'),
    path('opportunity/priority-items', PriorityItemsView.as_view(), name='opportunity-priority-items'),
    path('ai/explain-signal', ExplainSignalView.as_view(), name='ai-explain-signal'),
    path('report/daily-summary', DailySummaryView.as_view(), name='report-daily-summary'),
    path('state/snapshot', StateSnapshotView.as_view(), name='state-snapshot'),
    # Actions bus (prototype; not exposed in openapi.yaml to keep op count)
    path('actions/query', ActionsQueryView.as_view(), name='actions-query'),
    # Read-only alias to avoid runtime consent prompts for GET
    path('actions/read', ActionsQueryView.as_view(), name='actions-read'),
    path('actions/mutate', ActionsMutateView.as_view(), name='actions-mutate'),
    # Serve slim OpenAPI for Actions
    path('openapi.actions.yaml', ActionsSpecView.as_view(), name='actions-openapi-spec'),
]
