from django.urls import path
from .views import TicksBufferView, RiskEvaluateView, LiveCheckView, ReadyCheckView

urlpatterns = [
    path("ticks/buffer/", TicksBufferView.as_view(), name="ticks-buffer"),
    path("risk/evaluate/", RiskEvaluateView.as_view(), name="risk-evaluate"),
    path("health/live/", LiveCheckView.as_view(), name="health-live"),
    path("health/ready/", ReadyCheckView.as_view(), name="health-ready"),
]
