from django.urls import path
from .views import PulseStatus, PulseDetail

urlpatterns = [
    path('feed/pulse-status', PulseStatus.as_view(), name='pulse-status'),
    path('feed/pulse-detail', PulseDetail.as_view(), name='pulse-detail'),
]
