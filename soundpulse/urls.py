"""
URL configuration for soundpulse project.
"""
from django.contrib import admin
from django.urls import path, include

from django.http import JsonResponse

def home_view(request):
    return JsonResponse({
        "status": "online",
        "service": "SoundPulse MP3 Hub API Server",
        "version": "1.0.0",
        "endpoints": {
            "trending": "/api/trending",
            "search": "/api/search?q={query}",
            "mood_radio": "/api/radio/recommendations?mood={mood}",
            "lyrics": "/api/lyrics?title={title}&artist={artist}",
            "download": "/api/download?id={id}&bitrate=320k"
        }
    })

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

