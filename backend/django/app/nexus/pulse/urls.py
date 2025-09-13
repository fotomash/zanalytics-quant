from django.urls import path
from .views import (
    PulseStatus,
    PulseDetail,
    PulseWeights,
    PulseGateHits,
    BarsEnriched,
    EnrichmentConfig,
    ConfigureEnrichment,
    YFBars,
    TradeQualityDist,
    DiscordHealth,
)

urlpatterns = [
    path('feed/pulse-status', PulseStatus.as_view(), name='pulse-status'),
    path('feed/pulse-detail', PulseDetail.as_view(), name='pulse-detail'),
    path('feed/pulse-weights', PulseWeights.as_view(), name='pulse-weights'),
    path('feed/pulse-gate-hits', PulseGateHits.as_view(), name='pulse-gate-hits'),
    path('feed/bars-enriched', BarsEnriched.as_view(), name='bars-enriched'),
    path('feed/enrichment-config', EnrichmentConfig.as_view(), name='enrichment-config'),
    path('enrichment/configure', ConfigureEnrichment.as_view(), name='configure-enrichment'),
    path('feed/yf-bars', YFBars.as_view(), name='yf-bars'),
    path('feed/trade-quality', TradeQualityDist.as_view(), name='trade-quality'),
    # Health
    path('health/discord', DiscordHealth.as_view(), name='discord-health'),
]
