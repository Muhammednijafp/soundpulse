import urllib.parse
from pathlib import Path
from datetime import datetime
from django.http import HttpResponseRedirect, StreamingHttpResponse, JsonResponse, FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import (
    search_tracks,
    get_track_info,
    get_direct_audio_url,
    generate_mp3_stream,
    sanitize_filename,
    get_song_lyrics,
    get_local_network_info,
    get_mood_stations,
    get_mood_tracks,
    get_smart_recommendations
)
from .serializers import (
    TrackSerializer,
    SearchResponseSerializer,
    TrackInfoRequestSerializer,
    TrackDetailSerializer
)

TRENDING_QUERIES = [
  {
    'category': 'Malayalam Hip-Hop & Rap (MHR, Dabzee, Fejo)',
    'query': 'mhr malayalam rapper songs',
    'tag': 'MHR & Rap'
  },
  {
    'category': 'Latest Malayalam Hits',
    'query': 'latest malayalam songs 2025 2026',
    'tag': 'Malayalam'
  },
  {
    'category': 'Indian Indie & Hip-Hop',
    'query': 'indian hip hop rap trending songs',
    'tag': 'Desi Hip-Hop'
  },
  {
    'category': 'Global Trending Beats',
    'query': 'top viral songs 2026',
    'tag': 'Global'
  }
]

class HealthCheckAPIView(APIView):
    """Health check endpoint"""
    def get(self, request):
        return Response({
            'status': 'online',
            'backend': 'Django 5.1 & Django REST Framework',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': 'SoundPulse MP3 Search, AI Studio & Downloader API'
        })

class SearchAPIView(APIView):
    """Search tracks by keyword or artist name (e.g. MHR)"""
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        try:
            limit = int(request.query_params.get('limit', 16))
        except ValueError:
            limit = 16

        if not query:
            return Response(
                {'success': False, 'error': 'Search query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            results = search_tracks(query, limit=limit)
            return Response({
                'success': True,
                'query': query,
                'count': len(results),
                'tracks': results
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Search operation failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TrackInfoAPIView(APIView):
    """Inspect and extract detailed metadata from a YouTube / Song URL"""
    def post(self, request):
        url = request.data.get('url') or request.query_params.get('url') or request.query_params.get('id')
        if not url:
            return Response(
                {'success': False, 'error': 'A valid URL or track ID is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            track = get_track_info(url)
            return Response({'success': True, 'track': track})
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Could not parse track metadata.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        return self.post(request)

class StreamAudioAPIView(APIView):
    """Get direct audio stream URL and redirect web audio player natively"""
    def get(self, request):
        url_or_id = request.query_params.get('id') or request.query_params.get('url')
        if not url_or_id:
            return Response(
                {'success': False, 'error': 'Track "id" or "url" is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            direct_url = get_direct_audio_url(url_or_id)
            return HttpResponseRedirect(direct_url)
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Unable to stream audio.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DownloadMp3APIView(APIView):
    """Transcode and stream high-quality MP3 attachment directly to device Downloads folder"""
    def get(self, request):
        url_or_id = request.query_params.get('id') or request.query_params.get('url')
        bitrate = request.query_params.get('bitrate', '320k')

        if not url_or_id:
            return Response(
                {'success': False, 'error': 'Track "id" or "url" is required for download.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Fetch metadata for clean naming
        meta = None
        try:
            meta = get_track_info(url_or_id)
            track_title = meta.get('title', 'song')
            track_artist = meta.get('artist', 'audio')
            filename = sanitize_filename(f"{track_title} - {track_artist}") or 'download'
        except Exception:
            filename = 'download'

        encoded_filename = urllib.parse.quote(f"{filename}.mp3")

        # 2. Return StreamingHttpResponse with MP3 binary generator
        response = StreamingHttpResponse(
            generate_mp3_stream(url_or_id, bitrate=bitrate, meta=meta),
            content_type='audio/mpeg'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.mp3"; filename*=UTF-8\'\'{encoded_filename}'
        response['Cache-Control'] = 'no-cache'
        return response

class TrendingAPIView(APIView):
    """Trending playlists and charts"""
    def get(self, request):
        query = request.query_params.get('q', 'mhr malayalam rapper songs')
        try:
            tracks = search_tracks(query, limit=12)
            return Response({
                'success': True,
                'categories': TRENDING_QUERIES,
                'tracks': tracks
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Failed to fetch trending tracks.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LyricsAPIView(APIView):
    """
    Fetch synchronized (LRC) and plain song lyrics.
    Supports real-time karaoke tracking and line-by-line seek.
    """
    def get(self, request):
        title = request.query_params.get('title', '').strip()
        artist = request.query_params.get('artist', '').strip()
        track_id = request.query_params.get('id', '').strip()
        
        try:
            duration = float(request.query_params.get('duration', 0))
        except (ValueError, TypeError):
            duration = 0

        if not title and not track_id:
            return Response(
                {'success': False, 'error': 'Song "title" or track "id" is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If title is missing but id is provided, fetch title from track info
        if not title and track_id:
            try:
                info = get_track_info(track_id)
                title = info.get('title', '')
                artist = info.get('artist', '') or artist
                duration = info.get('duration', 0) or duration
            except Exception:
                pass

        try:
            lyrics_data = get_song_lyrics(
                title=title,
                artist=artist,
                duration=duration,
                target_url_or_id=track_id
            )
            return Response({
                'success': True,
                'lyrics': lyrics_data
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Failed to fetch lyrics.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NetworkInfoAPIView(APIView):
    """
    Returns local Wi-Fi IP address and network links for 1-scan mobile access.
    """
    def get(self, request):
        try:
            info = get_local_network_info()
            return Response({
                'success': True,
                'network': info
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Could not determine local network info.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MoodRadioAPIView(APIView):
    """
    Returns available mood stations and tracks for the selected mood radio.
    """
    def get(self, request):
        mood = request.query_params.get('mood', '').strip()
        limit = int(request.query_params.get('limit', 16))
        
        stations = get_mood_stations()
        
        if not mood:
            tracks = get_mood_tracks('late_night', limit=limit)
            return Response({
                'success': True,
                'stations': stations,
                'activeMood': 'late_night',
                'tracks': tracks
            })
        
        tracks = get_mood_tracks(mood, limit=limit)
        return Response({
            'success': True,
            'stations': stations,
            'activeMood': mood,
            'tracks': tracks
        })

class SmartRecommendationsAPIView(APIView):
    """
    Returns smart recommendations for DJ Autoplay given current playing track or mood.
    """
    def get(self, request):
        track_id = request.query_params.get('id', '')
        title = request.query_params.get('title', '')
        artist = request.query_params.get('artist', '')
        mood = request.query_params.get('mood', '')
        exclude_param = request.query_params.get('exclude', '')
        limit = int(request.query_params.get('limit', 10))
        
        exclude_ids = [x.strip() for x in exclude_param.split(',') if x.strip()]
        
        try:
            tracks = get_smart_recommendations(
                track_id=track_id,
                title=title,
                artist=artist,
                mood_key=mood,
                exclude_ids=exclude_ids,
                limit=limit
            )
            return Response({
                'success': True,
                'recommendations': tracks
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e) or 'Could not generate recommendations.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


