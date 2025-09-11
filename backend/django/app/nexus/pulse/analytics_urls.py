from django.urls import path
from .views import (
    TradesQuality,
    TradesSummary,
    TradesEfficiency,
    TradesBuckets,
    TradesSetups,
)

urlpatterns = [
    path('trades/quality', TradesQuality.as_view(), name='analytics-trades-quality'),
    path('trades/summary', TradesSummary.as_view(), name='analytics-trades-summary'),
    path('trades/efficiency', TradesEfficiency.as_view(), name='analytics-trades-efficiency'),
    path('trades/buckets', TradesBuckets.as_view(), name='analytics-trades-buckets'),
    path('trades/setups', TradesSetups.as_view(), name='analytics-trades-setups'),
]
