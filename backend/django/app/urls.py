from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from app.nexus.views import Healthz
from .api.views_wyckoff import wyckoff_score, wyckoff_health
from app import pulse_views
from .whisper_views import whisper_stream, whisper_ack, whisper_act, whisper_log

def health(request):
    return JsonResponse({"status": "ok"}, status=200)
    
urlpatterns = [
    # Admin & base
    path('admin/', admin.site.urls),

    # v1 api
    path('api/v1/', include('app.nexus.urls')),

    # Wyckoff endpoints
    path('api/pulse/wyckoff/score', wyckoff_score, name='wyckoff-score'),
    path('api/pulse/wyckoff/health', wyckoff_health, name='wyckoff-health'),

    # Robust health endpoint (readiness)
    path('api/pulse/health', Healthz.as_view(), name='pulse-health'),

    # Pulse API bundle
    path('api/pulse/', include('pulse_api.urls')),
]

urlpatterns += [
    path('api/pulse/score/', pulse_views.get_confluence_score, name='pulse_score'),
    path('api/pulse/risk/', pulse_views.get_risk_status, name='pulse_risk'),
    path('api/pulse/signals/', pulse_views.get_active_signals, name='pulse_signals'),
    path('api/pulse/process/', pulse_views.process_tick, name='pulse_process'),
    # Whisper API
    path('api/pulse/whispers', whisper_stream, name='whispers_stream'),
    path('api/pulse/whisper/ack', whisper_ack, name='whisper_ack'),
    path('api/pulse/whisper/act', whisper_act, name='whisper_act'),
    path('api/pulse/whispers/log', whisper_log, name='whisper_log'),
]
