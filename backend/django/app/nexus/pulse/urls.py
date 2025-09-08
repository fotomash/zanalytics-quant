from django.urls import path
from .views import PulseStatus, PulseDetail, PulseWeights, PulseGateHits

urlpatterns = [
    path('feed/pulse-status', PulseStatus.as_view(), name='pulse-status'),
    path('feed/pulse-detail', PulseDetail.as_view(), name='pulse-detail'),
    path('feed/pulse-weights', PulseWeights.as_view(), name='pulse-weights'),
    path('feed/pulse-gate-hits', PulseGateHits.as_view(), name='pulse-gate-hits'),
]
