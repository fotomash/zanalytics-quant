from django.urls import path
from .views import PulseStatus

urlpatterns = [
    path('feed/pulse-status', PulseStatus.as_view(), name='pulse-status'),
]

