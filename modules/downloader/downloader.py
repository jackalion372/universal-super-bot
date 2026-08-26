import os
import re
import asyncio
import uuid
import shutil
import html
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import yt_dlp
from core.config import DOWNLOADS_DIR, logger

SYSTEM_FFMPEG = shutil.which("ffmpeg")
if SYSTEM_FFMPEG:
    FFMPEG_EXE = SYSTEM_FFMPEG
else:
    try:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_EXE = "ffmpeg"

FFMPEG_DIR = str(Path(FFMPEG_EXE).parent)
if FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

URL_PATTERNS = {
    "instagram": re.compile(r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv|stories)/[\w\-]+)", re.IGNORECASE),
    "tiktok": re.compile(r"(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[\w\-@/]+)", re.IGNORECASE),
    "youtube": re.compile(r"(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w\-]+)", re.IGNORECASE),
    "pinterest": re.compile(r"(https?://(?:[a-z0-9]+\.)?pinterest\.(?:com|it|co\.uk|es|de|fr)/pin/[\w\-]+|https?://pin\.it/[\w\-]+)", re.IGNORECASE),
    "likee": re.compile(r"(https?://(?:[a-z0-9]+\.)?likee\.(?:video|com)/[\w\-@/]+)", re.IGNORECASE),
    "snapchat": re.compile(r"(https?://(?:www\.)?snapchat\.com/(?:spotlight|add)/[\w\-]+)", re.IGNORECASE)
}

def detect_platform(url: str) -> str:
    for platform, pattern in URL_PATTERNS.items():
        if pattern.search(url):
            return platform
    return "media"

async def download_media(url: str, extract_audio: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_download, url, extract_audio)

def _sync_download(url: str, extract_audio: bool = False) -> dict:
    file_id = uuid.uuid4().hex[:10]
    out_template = str(DOWNLOADS_DIR / f"{file_id}_%(title).50s.%(ext)s")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE,
        'noplaylist': True,
        'max_filesize': 49 * 1024 * 1024,
        'concurrent_fragment_downloads': 8,
        'buffersize': 1024 * 1024,
        'nocheckcertificate': True,
        'socket_timeout': 10,
        'http_headers': headers,
    }

    if extract_audio:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'bestvideo[filesize<48M]+bestaudio/best[filesize<48M]/best/b'

    # 1-Bosqich: yt-dlp yordamida yuklab olishga urinish
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                title = info.get('title', 'Media')
                duration = info.get('duration', 0)
                
                downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
                if downloaded_files:
                    filepath = downloaded_files[0]
                    is_audio = filepath.suffix.lower() in ['.mp3', '.m4a', '.aac', '.ogg', '.wav'] or extract_audio
                    is_image = filepath.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
                    return {
                        "success": True,
                        "file_path": str(filepath),
                        "title": title,
                        "duration": duration,
                        "is_audio": is_audio,
                        "is_image": is_image,
                        "platform": detect_platform(url)
                    }
    except Exception as e:
        logger.warning(f"yt-dlp initial attempt failed for {url}: {e}")

    # 2-Bosqich: Agar yt-dlp foto yoki video berolmasa, Web Scraper Fallback
    fallback_res = _scrape_fallback(url, file_id, headers)
    if fallback_res.get("success"):
        return fallback_res

    # 3-Bosqich: yt-dlp sodda fallback format bilan qayta urinish
    try:
        ydl_opts['format'] = 'b/best'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
            info = ydl2.extract_info(url, download=True)
            if info:
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
                if downloaded_files:
                    filepath = downloaded_files[0]
                    return {
                        "success": True,
                        "file_path": str(filepath),
                        "title": info.get('title', 'Media'),
                        "duration": info.get('duration', 0),
                        "is_audio": False,
                        "is_image": False,
                        "platform": detect_platform(url)
                    }
    except Exception:
        pass

    return {
        "success": False,
        "error": "Ushbu havola bo'yicha media topilmadi. Havola to'g'ri va ochiq profilga tegishli ekanligini tekshiring."
    }

def _scrape_fallback(url: str, file_id: str, headers: dict) -> dict:
    """HTML metadata scraper Pinterest, Instagram va boshqalar uchun"""
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return {"success": False}

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Sarlavhani topish
        title = "Media"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()[:60]
            
        # 1. Video meta teglarini tekshirish (og:video, og:video:secure_url)
        video_url = None
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '') or meta.get('name', '')
            if prop in ['og:video', 'og:video:secure_url', 'og:video:url', 'twitter:player:stream']:
                content = meta.get('content')
                if content and content.startswith('http'):
                    video_url = content
                    break
                    
        if video_url:
            v_resp = requests.get(video_url, headers=headers, timeout=15, stream=True)
            if v_resp.status_code == 200:
                v_path = str(DOWNLOADS_DIR / f"{file_id}_video.mp4")
                with open(v_path, 'wb') as f:
                    for chunk in v_resp.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                return {
                    "success": True,
                    "file_path": v_path,
                    "title": title,
                    "duration": 0,
                    "is_audio": False,
                    "is_image": False,
                    "platform": detect_platform(url)
                }

        # 2. Foto meta teglarini tekshirish (og:image, twitter:image)
        image_url = None
        for meta in soup.find_all('meta'):
            prop = meta.get('property', '') or meta.get('name', '')
            if prop in ['og:image', 'twitter:image', 'og:image:secure_url']:
                content = meta.get('content')
                if content and content.startswith('http'):
                    image_url = content
                    break
                    
        if image_url:
            # Pinterest original HD rasmini olish
            if "pinimg.com" in image_url:
                image_url = re.sub(r'/(?:736x|564x|474x|236x)/', '/originals/', image_url)
                
            img_resp = requests.get(image_url, headers=headers, timeout=10)
            if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                ext = ".jpg"
                if "png" in image_url.lower():
                    ext = ".png"
                elif "webp" in image_url.lower():
                    ext = ".webp"
                img_path = str(DOWNLOADS_DIR / f"{file_id}_image{ext}")
                with open(img_path, 'wb') as f:
                    f.write(img_resp.content)
                return {
                    "success": True,
                    "file_path": img_path,
                    "title": title,
                    "duration": 0,
                    "is_audio": False,
                    "is_image": True,
                    "platform": detect_platform(url)
                }
    except Exception as e:
        logger.warning(f"Scrape fallback error: {e}")
        
    return {"success": False}
