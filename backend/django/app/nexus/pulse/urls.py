from django.urls import path
from .views import (
    PulseStatus, PulseDetail, PulseWeights, PulseGateHits, BarsEnriched, YFBars,
    TradeQualityDist,
    TradesQuality, TradesSummary, TradesEfficiency, TradesBuckets, TradesSetups,
    TelegramHealth,
)

urlpatterns = [
    path('feed/pulse-status', PulseStatus.as_view(), name='pulse-status'),
    path('feed/pulse-detail', PulseDetail.as_view(), name='pulse-detail'),
    path('feed/pulse-weights', PulseWeights.as_view(), name='pulse-weights'),
    path('feed/pulse-gate-hits', PulseGateHits.as_view(), name='pulse-gate-hits'),
    path('feed/bars-enriched', BarsEnriched.as_view(), name='bars-enriched'),
    path('feed/yf-bars', YFBars.as_view(), name='yf-bars'),
    path('feed/trade-quality', TradeQualityDist.as_view(), name='trade-quality'),
    # Analytics (phase 1)
    path('analytics/trades/quality', TradesQuality.as_view(), name='analytics-trades-quality'),
    path('analytics/trades/summary', TradesSummary.as_view(), name='analytics-trades-summary'),
    path('analytics/trades/efficiency', TradesEfficiency.as_view(), name='analytics-trades-efficiency'),
    path('analytics/trades/buckets', TradesBuckets.as_view(), name='analytics-trades-buckets'),
    path('analytics/trades/setups', TradesSetups.as_view(), name='analytics-trades-setups'),
    # Health
    path('health/telegram', TelegramHealth.as_view(), name='telegram-health'),
]
