from django.contrib import admin
from django.urls import path, include
from app.nexus.views import PingView
from .api.views_wyckoff import wyckoff_score, wyckoff_health

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/ping/', PingView.as_view(), name='api-ping'),
    path('api/v1/', include('app.nexus.urls')),
]

urlpatterns += [
    path('api/pulse/wyckoff/score', wyckoff_score),
    path('api/pulse/wyckoff/health', wyckoff_health),
]