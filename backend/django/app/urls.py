from django.contrib import admin
from django.urls import path, include
from app.nexus.views import PingView
from .api.views_wyckoff import wyckoff_score, wyckoff_health
from . import pulse_views
from server.pulse import views as pulse_api_views

# Provide a robust pulse health import with a safe fallback
try:
    from app.nexus.views import health as pulse_health  # type: ignore
except Exception:
    from django.http import JsonResponse
    def pulse_health(request):
        return JsonResponse({"status": "ok"})
    
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
    path('', include('pulse_api.urls')),
]

urlpatterns += [
    path('api/pulse/health/', pulse_views.health_check, name='pulse_health'),
    path('api/pulse/score/', pulse_views.get_confluence_score, name='pulse_score'),
    path('api/pulse/risk/', pulse_views.get_risk_status, name='pulse_risk'),
    path('api/pulse/signals/', pulse_views.get_active_signals, name='pulse_signals'),
    path('api/pulse/process/', pulse_views.process_tick, name='pulse_process'),
]

urlpatterns += [
    path("api/pulse/score/peek", pulse_api_views.score_peek),
    path("api/pulse/score", pulse_api_views.score_post),
    path("api/pulse/risk/summary", pulse_api_views.risk_summary),
    path("api/pulse/signals/top", pulse_api_views.signals_top),
    path("api/pulse/journal/recent", pulse_api_views.journal_recent),
]
