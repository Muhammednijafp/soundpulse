import re
import subprocess
import yt_dlp
import os
import json
import socket
import urllib.request
import urllib.parse

def format_duration(seconds):
    """Format duration in seconds to MM:SS or HH:MM:SS"""
    if not seconds or not isinstance(seconds, (int, float)):
        return '0:00'
    sec = int(seconds)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_views(views):
    """Format view counts into readable K/M/Cr strings"""
    if not views or not isinstance(views, (int, float)):
        return 'N/A'
    if views >= 10000000:
        return f"{views / 10000000:.1f}Cr"
    if views >= 1000000:
        return f"{views / 1000000:.1f}M"
    if views >= 1000:
        return f"{views / 1000:.1f}K"
    return str(views)

def sanitize_filename(name):
    """Sanitize filename to prevent illegal filesystem/header characters"""
    if not name:
        return "song_audio"
    # Remove characters like \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', '', str(name))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized[:100]

def search_tracks(query, limit=15):
    """Search tracks using yt-dlp native Python API"""
    if not query or not query.strip():
        return []
    
    clean_query = query.strip()
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
    }

    search_query = f"ytsearch{limit}:{clean_query}"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
        except Exception as e:
            print(f"Error during yt-dlp search: {e}")
            return []

    if not info or 'entries' not in info:
        return []

    tracks = []
    for item in info['entries']:
        if not item:
            continue
        track_id = item.get('id') or ''
        if not track_id and item.get('url'):
            track_id = item['url'].split('/')[-1].split('v=')[-1]
        
        thumbnail = f"https://i.ytimg.com/vi/{track_id}/hqdefault.jpg"
        thumbnails = item.get('thumbnails')
        if thumbnails and len(thumbnails) > 0:
            thumbnail = thumbnails[-1].get('url') or thumbnail

        duration = item.get('duration') or 0
        views = item.get('view_count') or 0

        tracks.append({
            'id': track_id,
            'title': item.get('title') or 'Unknown Title',
            'artist': item.get('channel') or item.get('uploader') or 'Unknown Artist',
            'channelUrl': item.get('channel_url') or (f"https://www.youtube.com/channel/{item.get('channel_id')}" if item.get('channel_id') else None),
            'duration': duration,
            'durationFormatted': format_duration(duration),
            'views': views,
            'viewsFormatted': format_views(views),
            'thumbnail': thumbnail,
            'url': item.get('url') if item.get('url', '').startswith('http') else f"https://www.youtube.com/watch?v={track_id}",
            'isVerified': item.get('channel_is_verified', False)
        })

    return tracks

def get_cookie_file():
    """Dynamically parse and format Netscape cookie file from environment variable"""
    cookies_env = os.getenv('YOUTUBE_COOKIES', '').strip()
    if not cookies_env:
        return None

    if os.path.exists(cookies_env):
        return cookies_env

    try:
        raw_content = cookies_env.replace('\\n', '\n').replace('\\t', '\t')
        if '# Netscape' not in raw_content:
            raw_content = "# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n" + raw_content

        cookie_tmp = Path(tempfile.gettempdir()) / 'yt_cookies.txt'
        cookie_tmp.write_text(raw_content, encoding='utf-8')
        return str(cookie_tmp)
    except Exception as e:
        print(f"Error preparing cookie file: {e}")
        return None

def get_track_info(target_url_or_id):
    """Extract full track metadata for any video ID or URL"""
    target = target_url_or_id.strip()
    if not target.startswith('http://') and not target.startswith('https://'):
        target = f"https://www.youtube.com/watch?v={target}"

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ignoreerrors': True,
        'skip_download': True,
        'js_runtimes': {'node': {}, 'deno': {}, 'quickjs': {}},
    }
    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=False)

    if not info:
        raise ValueError("Could not retrieve metadata for the provided URL.")

    track_id = info.get('id', '')
    thumbnail = f"https://i.ytimg.com/vi/{track_id}/maxresdefault.jpg"
    if info.get('thumbnail'):
        thumbnail = info.get('thumbnail')
    elif info.get('thumbnails'):
        thumbnail = info['thumbnails'][-1].get('url', thumbnail)

    duration = info.get('duration') or 0
    views = info.get('view_count') or 0

    return {
        'id': track_id,
        'title': info.get('title') or 'Unknown Track',
        'artist': info.get('artist') or info.get('creator') or info.get('channel') or info.get('uploader') or 'Unknown Artist',
        'album': info.get('album'),
        'channel': info.get('channel') or info.get('uploader') or 'Unknown Channel',
        'duration': duration,
        'durationFormatted': format_duration(duration),
        'views': views,
        'viewsFormatted': format_views(views),
        'thumbnail': thumbnail,
        'uploadDate': info.get('upload_date'),
        'description': (info.get('description') or '')[:300],
        'url': info.get('webpage_url') or target,
        'formatsAvailable': ['320 kbps (Studio MP3)', '192 kbps (High MP3)', '128 kbps (Standard MP3)']
    }

def get_direct_audio_stream_info(target_url_or_id):
    """
    Extract the direct audio stream URL and required HTTP headers
    """
    target = target_url_or_id.strip()
    if not target.startswith('http://') and not target.startswith('https://'):
        target = f"https://www.youtube.com/watch?v={target}"

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'js_runtimes': {'node': {}, 'deno': {}, 'quickjs': {}},
    }
    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target, download=False)
        if not info:
            raise ValueError("Could not obtain direct audio stream URL.")
            
        # Select best audio stream url
        url = info.get('url')
        if not url and info.get('formats'):
            audio_fmts = [f for f in info['formats'] if f.get('acodec') != 'none' and f.get('url')]
            if audio_fmts:
                audio_fmts.sort(key=lambda x: x.get('abr') or 0, reverse=True)
                url = audio_fmts[0].get('url')
                
        if not url:
            raise ValueError("Could not obtain direct audio stream URL.")
            
        return {
            'url': url,
            'headers': info.get('http_headers', {}),
            'title': info.get('title') or 'song',
            'artist': info.get('artist') or info.get('channel') or info.get('uploader') or 'artist',
            'duration': info.get('duration') or 0
        }

def get_direct_audio_url(target_url_or_id):
    """Get the direct high-speed audio stream link for web player"""
    info = get_direct_audio_stream_info(target_url_or_id)
    return info['url']

import tempfile
from pathlib import Path

AUDIO_CACHE_DIR = Path(tempfile.gettempdir()) / 'soundpulse_cache'
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def download_track_mp3(target_url_or_id, bitrate='320k'):
    """
    Downloads and converts track to genuine 320k MP3 using yt-dlp native engine.
    Caches the file locally for ultra-fast repeated streaming and downloading.
    """
    clean_id = sanitize_filename(target_url_or_id.split('v=')[-1].split('/')[-1])
    mp3_path = AUDIO_CACHE_DIR / f"{clean_id}_{bitrate}.mp3"
    
    if mp3_path.exists() and mp3_path.stat().st_size > 10000:
        return str(mp3_path)
    
    target = target_url_or_id.strip()
    if not target.startswith('http://') and not target.startswith('https://'):
        target = f"https://www.youtube.com/watch?v={target}"
        
    ffmpeg_bin = None
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
        
    outtmpl = str(AUDIO_CACHE_DIR / f"{clean_id}_{bitrate}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'js_runtimes': {'node': {}, 'deno': {}, 'quickjs': {}},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': bitrate.replace('k', ''),
        }],
    }
    if ffmpeg_bin:
        ydl_opts['ffmpeg_location'] = ffmpeg_bin
    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([target])
        
    if mp3_path.exists() and mp3_path.stat().st_size > 0:
        return str(mp3_path)
        
    # Check for any created audio file in cache matching this id
    for f in AUDIO_CACHE_DIR.glob(f"{clean_id}_{bitrate}.*"):
        if f.stat().st_size > 0:
            return str(f)
            
    raise RuntimeError(f"Could not extract audio for track: {target_url_or_id}")

def clean_lyrics_query(text):
    """Clean video titles, buzzwords, and bracketed tags to improve lyrics search hits"""
    if not text:
        return ''
    cleaned = re.sub(r'\s*[\(\[\{][^\)\]\}]*[\)\]\}]\s*', ' ', str(text))
    cleaned = re.sub(r'(?i)\b(official video|music video|lyric video|audio|full song|hd|4k|remix|feat\.|ft\.|prod\.)\b', ' ', cleaned)
    cleaned = re.sub(r'[|\\/:]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def get_song_lyrics(title, artist='', duration=0, target_url_or_id=None):
    """
    Fetch synchronized (LRC) and plain text lyrics for a given song.
    Uses LRCLIB with exact match and smart fallback search.
    """
    clean_title = clean_lyrics_query(title)
    clean_artist = clean_lyrics_query(artist)
    
    # 1. Try exact lookup on LRCLIB
    if clean_title and clean_artist:
        params = {'track_name': clean_title, 'artist_name': clean_artist}
        if duration and duration > 0:
            params['duration'] = int(duration)
        query_str = urllib.parse.urlencode(params)
        url = f"https://lrclib.net/api/get?{query_str}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SoundPulse/1.0 (https://soundpulse.local)'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and (data.get('syncedLyrics') or data.get('plainLyrics')):
                    return {
                        'found': True,
                        'title': data.get('trackName') or clean_title,
                        'artist': data.get('artistName') or clean_artist,
                        'syncedLyrics': data.get('syncedLyrics') or None,
                        'plainLyrics': data.get('plainLyrics') or '',
                        'hasSynced': bool(data.get('syncedLyrics')),
                        'source': 'LRCLIB'
                    }
        except Exception:
            pass

    # 2. Try search lookup on LRCLIB
    search_queries = [
        f"{clean_title} {clean_artist}".strip(),
        clean_title
    ]
    for q in search_queries:
        if not q:
            continue
        s_query = urllib.parse.urlencode({'q': q})
        s_url = f"https://lrclib.net/api/search?{s_query}"
        try:
            req = urllib.request.Request(s_url, headers={'User-Agent': 'SoundPulse/1.0 (https://soundpulse.local)'})
            with urllib.request.urlopen(req, timeout=4) as response:
                items = json.loads(response.read().decode('utf-8'))
                if items and len(items) > 0:
                    for item in items:
                        if item.get('syncedLyrics') or item.get('plainLyrics'):
                            return {
                                'found': True,
                                'title': item.get('trackName') or clean_title,
                                'artist': item.get('artistName') or clean_artist,
                                'syncedLyrics': item.get('syncedLyrics') or None,
                                'plainLyrics': item.get('plainLyrics') or '',
                                'hasSynced': bool(item.get('syncedLyrics')),
                                'source': 'LRCLIB'
                            }
        except Exception:
            pass

    # 3. Fallback: check YouTube video description if lyrics are present
    if target_url_or_id:
        try:
            info = get_track_info(target_url_or_id)
            desc = info.get('description', '')
            if 'lyrics' in desc.lower() or 'lyric' in desc.lower():
                return {
                    'found': True,
                    'title': info.get('title') or title,
                    'artist': info.get('artist') or artist,
                    'syncedLyrics': None,
                    'plainLyrics': desc,
                    'hasSynced': False,
                    'source': 'Description'
                }
        except Exception:
            pass

    return {
        'found': False,
        'title': title,
        'artist': artist,
        'syncedLyrics': None,
        'plainLyrics': '',
        'hasSynced': False,
        'error': 'No synchronized lyrics found for this track.'
    }

def get_local_network_info():
    """Detect local IP address and return mobile network sharing URLs"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    
    return {
        'localIp': ip,
        'port': 3000,
        'mobileUrl': f"http://{ip}:3000",
        'backendUrl': f"http://{ip}:8000"
    }

# Curated Mood Stations Configuration
MOOD_PRESETS = {
    'late_night': {
        'id': 'late_night',
        'title': 'Late Night Drive',
        'subtitle': 'Synthwave, Slowed & Reverb Melodies',
        'icon': 'Moon',
        'badge': 'Atmospheric',
        'color': 'from-indigo-600 via-purple-600 to-pink-500',
        'glow': 'rgba(147, 51, 234, 0.4)',
        'query': 'late night drive chill synthwave slow reverb songs'
    },
    'gym_energy': {
        'id': 'gym_energy',
        'title': 'Gym & High Energy',
        'subtitle': 'Phonk, Bass-Heavy Trap & EDM',
        'icon': 'Flame',
        'badge': 'High BPM',
        'color': 'from-red-600 via-orange-600 to-amber-500',
        'glow': 'rgba(239, 68, 68, 0.4)',
        'query': 'workout phonk bass boosted gym trap rap songs'
    },
    'chill_lofi': {
        'id': 'chill_lofi',
        'title': 'Lo-Fi & Study Chill',
        'subtitle': 'Warm Acoustic & Coffeehouse Beats',
        'icon': 'Coffee',
        'badge': 'Relaxing',
        'color': 'from-amber-600 via-orange-500 to-yellow-400',
        'glow': 'rgba(245, 158, 11, 0.4)',
        'query': 'lofi chill beats acoustic relaxing study songs'
    },
    'party_dance': {
        'id': 'party_dance',
        'title': 'Party & Dance Club',
        'subtitle': 'Club Anthems & High-BPM Dance Hits',
        'icon': 'Sparkles',
        'badge': 'Club Beats',
        'color': 'from-cyan-500 via-blue-600 to-fuchsia-600',
        'glow': 'rgba(6, 182, 212, 0.4)',
        'query': 'club party dance edm high bpm malayalam tamil hits'
    },
    'soulful': {
        'id': 'soulful',
        'title': 'Soulful & Emotional',
        'subtitle': 'Heartfelt Melodies & Acoustic Ballads',
        'icon': 'HeartHandshake',
        'badge': 'Acoustic',
        'color': 'from-rose-600 via-pink-600 to-purple-600',
        'glow': 'rgba(244, 63, 94, 0.4)',
        'query': 'soulful acoustic emotional sad melodies love songs'
    },
    'malayalam_rap': {
        'id': 'malayalam_rap',
        'title': 'Malayalam Hip-Hop & Rap',
        'subtitle': 'MHR, Dabzee, Fejo, Baby Jean & Hanumankind',
        'icon': 'Mic2',
        'badge': 'Hip-Hop',
        'color': 'from-emerald-600 via-teal-600 to-cyan-500',
        'glow': 'rgba(16, 185, 129, 0.4)',
        'query': 'malayalam rap hip hop mhr dabzee fejo thirumali baby jean songs'
    },
    'retro_90s': {
        'id': 'retro_90s',
        'title': '90s & 2000s Evergreen Gold',
        'subtitle': 'Timeless Classics & Golden Era Superhits',
        'icon': 'Disc3',
        'badge': 'Classics',
        'color': 'from-amber-700 via-yellow-600 to-orange-600',
        'glow': 'rgba(217, 119, 6, 0.4)',
        'query': '90s 2000s evergreen classic superhit melodies songs'
    },
    'romantic': {
        'id': 'romantic',
        'title': 'Romantic Melodies',
        'subtitle': 'Sweet Love Hits & Trending Duets',
        'icon': 'Heart',
        'badge': 'Love Vibes',
        'color': 'from-pink-600 via-rose-500 to-red-500',
        'glow': 'rgba(236, 72, 153, 0.4)',
        'query': 'romantic love melody songs trending malayalam tamil hindi'
    }
}

def get_mood_stations():
    """Return list of available mood stations metadata"""
    return list(MOOD_PRESETS.values())

def get_mood_tracks(mood_key='late_night', limit=16):
    """Fetch tracks for a specific mood station"""
    preset = MOOD_PRESETS.get(mood_key)
    if not preset:
        preset = MOOD_PRESETS['late_night']
    query = preset['query']
    return search_tracks(query, limit=limit)

def get_smart_recommendations(track_id=None, title=None, artist=None, mood_key=None, exclude_ids=None, limit=10):
    """Generate smart DJ recommendations based on current track or mood for seamless Autoplay"""
    exclude_set = set(exclude_ids or [])
    if track_id:
        exclude_set.add(track_id)
    
    clean_title = clean_lyrics_query(title) if title else ''
    clean_artist = clean_lyrics_query(artist) if artist else ''
    
    queries = []
    if clean_artist and clean_artist.lower() not in ['unknown', 'various']:
        queries.append(f"{clean_artist} best songs")
    if clean_title and clean_artist:
        queries.append(f"{clean_artist} {clean_title} playlist")
    elif clean_title:
        queries.append(f"{clean_title} similar songs")
    
    if mood_key and mood_key in MOOD_PRESETS:
        queries.append(MOOD_PRESETS[mood_key]['query'])
    
    if not queries:
        queries.append("trending malayalam global music hits")
    
    # Run search on primary query
    primary_query = queries[0]
    tracks = search_tracks(primary_query, limit=limit + 5)
    
    # Filter out excluded tracks
    filtered_tracks = [t for t in tracks if t.get('id') not in exclude_set]
    
    # If not enough tracks and secondary query available, search more
    if len(filtered_tracks) < limit and len(queries) > 1:
        extra_tracks = search_tracks(queries[1], limit=limit)
        for t in extra_tracks:
            if t.get('id') not in exclude_set and not any(f['id'] == t.get('id') for f in filtered_tracks):
                filtered_tracks.append(t)
                if len(filtered_tracks) >= limit:
                    break
                    
    return filtered_tracks[:limit]



