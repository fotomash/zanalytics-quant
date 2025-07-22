from django.contrib import admin
from django.urls import path, include
from app.nexus.views import PingView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ping/', PingView.as_view(), name='api-ping'),
    path('v1/', include('app.nexus.urls')),
]