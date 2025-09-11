from django.urls import path
from . import views

urlpatterns = [
    path("health", views.pulse_health, name="pulse_health"),
    path("score", views.score_post, name="pulse_score_post"),
    path("score/peek", views.score_peek, name="pulse_score_peek"),
    path("risk/summary", views.risk_summary, name="pulse_risk_summary"),
    path("risk/update", views.risk_update, name="pulse_risk_update"),
    path("risk/check", views.risk_check, name="pulse_risk_check"),
    path("signals/top", views.signals_top, name="pulse_signals_top"),
    path("journal/recent", views.pulse_journal, name="pulse_journal_recent"),
    path("strategy/match", views.strategy_match, name="pulse_strategy_match"),
    path("ticks", views.tick_buffer, name="pulse_tick_buffer"),
    path("adapter/status", views.adapter_status, name="pulse_adapter_status"),
]
