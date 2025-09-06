from django.urls import path
from . import views

urlpatterns = [
    path("api/strategy/match", views.strategy_match),
    path("api/pulse/score", views.score_peek),
]
