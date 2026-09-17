from django.urls import path, re_path
from .views import (
    HealthCheckAPIView,
    SearchAPIView,
    TrackInfoAPIView,
    StreamAudioAPIView,
    DownloadMp3APIView,
    TrendingAPIView,
    LyricsAPIView,
    NetworkInfoAPIView,
    MoodRadioAPIView,
    SmartRecommendationsAPIView
)

urlpatterns = [
    re_path(r'^health/?$', HealthCheckAPIView.as_view(), name='health'),
    re_path(r'^search/?$', SearchAPIView.as_view(), name='search'),
    re_path(r'^info/?$', TrackInfoAPIView.as_view(), name='info'),
    re_path(r'^stream/?$', StreamAudioAPIView.as_view(), name='stream'),
    re_path(r'^download/?$', DownloadMp3APIView.as_view(), name='download'),
    re_path(r'^lyrics/?$', LyricsAPIView.as_view(), name='lyrics'),
    re_path(r'^network-info/?$', NetworkInfoAPIView.as_view(), name='network-info'),
    re_path(r'^trending/?$', TrendingAPIView.as_view(), name='trending'),
    re_path(r'^radio/tracks/?$', MoodRadioAPIView.as_view(), name='radio-tracks'),
    re_path(r'^radio/recommendations/?$', SmartRecommendationsAPIView.as_view(), name='radio-recommendations'),
]
