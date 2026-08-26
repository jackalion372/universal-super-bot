import os
import re
import asyncio
import uuid
import shutil
import html
from pathlib import Path
import yt_dlp
import aiohttp
from core.config import DOWNLOADS_DIR, logger

# System FFmpeg birinchi tekshiriladi
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
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE if SYSTEM_FFMPEG else FFMPEG_EXE,
        'noplaylist': True,
        'max_filesize': 49 * 1024 * 1024, # 49MB max Telegram bot limit
        'concurrent_fragment_downloads': 8,
        'buffersize': 1024 * 1024,
        'nocheckcertificate': True,
        'socket_timeout': 15,
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
        # Har qanday platforma uchun universal format fallbacks
        ydl_opts['format'] = 'bestvideo[filesize<48M]+bestaudio/best[filesize<48M]/best/b'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            title = info.get('title', 'Media')
            duration = info.get('duration', 0)
            
            downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
            if not downloaded_files:
                # Foto yoki Thumbnail yuklash (Pinterest/Instagram Rasm postlar)
                thumbnail = info.get('thumbnail') or info.get('url')
                if thumbnail:
                    import requests
                    resp = requests.get(thumbnail, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        img_path = str(DOWNLOADS_DIR / f"{file_id}_image.jpg")
                        with open(img_path, 'wb') as f:
                            f.write(resp.content)
                        return {
                            "success": True,
                            "file_path": img_path,
                            "title": title,
                            "duration": 0,
                            "is_audio": False,
                            "is_image": True,
                            "platform": detect_platform(url)
                        }
                return {"success": False, "error": "Media fayli topilmadi yoki hajmi 50MB dan katta."}
            
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
        logger.error(f"Download error for {url}: {e}")
        # Takroriy urinish fallback format
        if not extract_audio:
            try:
                ydl_opts['format'] = 'b/best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info = ydl2.extract_info(url, download=True)
                    if 'entries' in info and info['entries']:
                        info = info['entries'][0]
                    title = info.get('title', 'Media')
                    downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
                    if downloaded_files:
                        filepath = downloaded_files[0]
                        return {
                            "success": True,
                            "file_path": str(filepath),
                            "title": title,
                            "duration": info.get('duration', 0),
                            "is_audio": False,
                            "is_image": False,
                            "platform": detect_platform(url)
                        }
            except Exception as e2:
                pass
        return {"success": False, "error": f"Yuklab olishda xatolik yuz berdi: {str(e)[:100]}"}
