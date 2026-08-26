import os
import re
import asyncio
import uuid
from pathlib import Path
import yt_dlp
import aiohttp
import imageio_ffmpeg
from core.config import DOWNLOADS_DIR, logger

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
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
    
    # Maksimal tezlik uchun optimallashtirilgan parametrlar
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE,
        'noplaylist': True,
        'max_filesize': 50 * 1024 * 1024,
        'concurrent_fragment_downloads': 16, # Ko'p oqimli tezkor yuklash
        'buffersize': 1024 * 1024,
        'http_chunk_size': 10485760,
        'nocheckcertificate': True,
        'socket_timeout': 10,
    }

    if extract_audio:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/b/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            title = info.get('title', 'Media')
            duration = info.get('duration', 0)
            
            downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
            if not downloaded_files:
                thumbnail = info.get('thumbnail')
                if thumbnail:
                    import requests
                    resp = requests.get(thumbnail, timeout=5)
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
                return {"success": False, "error": "Fayl yuklab olinmadi"}
            
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
        return {"success": False, "error": str(e)}
