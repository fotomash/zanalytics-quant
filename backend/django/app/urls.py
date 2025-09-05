from django.contrib import admin
from django.urls import path, include
from app.nexus.views import PingView
from .api.views_wyckoff import wyckoff_score, wyckoff_health
from app.nexus.views import health as pulse_health

urlpatterns = [
    # Admin & base
    path('admin/', admin.site.urls),

    # v1 api
    path('api/v1/ping/', PingView.as_view(), name='api-ping'),
    path('api/v1/', include('app.nexus.urls')),

    # Wyckoff endpoints
    path('api/pulse/wyckoff/score', wyckoff_score, name='wyckoff-score'),
    path('api/pulse/wyckoff/health', wyckoff_health, name='wyckoff-health'),

    # Generic health aliases used by monitors
    path('api/pulse/health', pulse_health, name='pulse-health'),
    path('api/pulse/health/', pulse_health, name='pulse-health-slash'),
]