from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TradeViewSet,
    SendMarketOrderView,
    ModifySLTPView,
    TickViewSet,
    BarViewSet,
    SymbolListView,
    TimeframeListView,
    DashboardDataView,
    JournalEntryView,
)

router = DefaultRouter()
router.register(r'trades', TradeViewSet)
router.register(r'ticks', TickViewSet)
router.register(r'bars', BarViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('send_market_order/', SendMarketOrderView.as_view(), name='send_market_order'),
    path('modify_sl_tp/', ModifySLTPView.as_view(), name='modify_sl_tp'),
    path('symbols/', SymbolListView.as_view(), name='symbols'),
    path('timeframes/', TimeframeListView.as_view(), name='timeframes'),
    path('dashboard-data/', DashboardDataView.as_view(), name='dashboard-data'),
    path('journal/', JournalEntryView.as_view(), name='journal'),
]
