from django.urls import path
from . import views

urlpatterns = [
    path("api/pulse/health", views.pulse_health),
    path("api/pulse/score", views.score_peek),  # ✅ Fixed this
    path("api/ticks/buffer", views.tick_buffer),
    path("api/pulse/risk-check", views.risk_check),
    path("api/pulse/risk-summary", views.risk_summary),
    path("api/pulse/signals-top", views.signals_top),
    path("api/pulse/adapter-status", views.adapter_status),
    path("api/pulse/journal", views.pulse_journal),
    path("api/strategy/match", views.strategy_match),
]