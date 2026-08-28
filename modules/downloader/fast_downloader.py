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
    "snapchat": re.compile(r"(https?://(?:www\.)?snapchat\.com/(?:spotlight|add)/[\w\-]+)", re.IGNORECASE),
    "threads": re.compile(r"(https?://(?:www\.)?threads\.net/[\w\-@/]+)", re.IGNORECASE)
}

def detect_platform(url: str) -> str:
    for platform, pattern in URL_PATTERNS.items():
        if pattern.search(url):
            return platform
    return "media"

def shortcode_to_id(shortcode: str) -> int:
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    media_id = 0
    for char in shortcode:
        if char in alphabet:
            media_id = (media_id * 64) + alphabet.index(char)
    return media_id

async def fast_download_media(url: str, extract_audio: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_fast_download, url, extract_audio)

def _sync_fast_download(url: str, extract_audio: bool = False) -> dict:
    platform = detect_platform(url)
    
    # 1. TikTok Engine
    if platform == "tiktok":
        res = _fetch_tiktok_tikwm(url, extract_audio)
        if res.get("success"):
            return res

    # 2. Instagram Engine (Photo Posts, Reels, Karusel Albomlar)
    if platform == "instagram":
        res = _fetch_instagram_fast(url, extract_audio)
        if res.get("success"):
            return res

    # 3. Pinterest Engine
    if platform == "pinterest":
        res = _fetch_pinterest_fast(url)
        if res.get("success"):
            return res

    # 4. YouTube Engine
    if platform == "youtube":
        res = _fetch_youtube_fast(url, extract_audio)
        if res.get("success"):
            return res

    # 5. Public API Engine
    res_api = _fetch_cobalt_public_api(url, extract_audio)
    if res_api.get("success"):
        return res_api

    # 6. yt-dlp Direct Stream Engine
    res_ytdl = _fetch_ytdlp_fast(url, extract_audio)
    if res_ytdl.get("success"):
        return res_ytdl

    # 7. HTML Meta Scraper Engine
    res_scrape = _fetch_html_scrape(url)
    if res_scrape.get("success"):
        return res_scrape

    return {
        "success": False,
        "error": "Kechirasiz, ushbu media yuklanmadi. Havola to'g'ri va ochiq profilga tegishli ekanligini tekshiring."
    }

# ==================== PLATFORM ENGINES ====================

def _fetch_tiktok_tikwm(url: str, extract_audio: bool) -> dict:
    try:
        api_url = "https://www.tikwm.com/api/"
        resp = requests.post(api_url, data={"url": url, "hd": 1}, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data:
                title = data.get("title", "TikTok Media")
                if extract_audio and data.get("music"):
                    return {
                        "success": True,
                        "direct_url": data.get("music"),
                        "title": title,
                        "is_audio": True,
                        "is_image": False,
                        "platform": "tiktok"
                    }
                images = data.get("images", [])
                if images and isinstance(images, list) and len(images) > 0:
                    return {
                        "success": True,
                        "is_album": True,
                        "media_list": [{"type": "photo", "url": img} for img in images[:10]],
                        "title": title,
                        "is_audio": False,
                        "is_image": True,
                        "platform": "tiktok"
                    }
                play_url = data.get("hdplay") or data.get("play")
                if play_url:
                    return {
                        "success": True,
                        "direct_url": play_url,
                        "title": title,
                        "is_audio": False,
                        "is_image": False,
                        "platform": "tiktok"
                    }
    except Exception as e:
        logger.warning(f"Tikwm error: {e}")
    return {"success": False}

def _fetch_instagram_fast(url: str, extract_audio: bool) -> dict:
    """Instagram Photo Posts & Karusel Albomlarini to'liq 1080p HD shaklda ajratish"""
    try:
        match = re.search(r"instagram\.com/(?:p|reel|tv)/([\w\-]+)", url, re.IGNORECASE)
        if not match:
            return {"success": False}
            
        shortcode = match.group(1)
        media_id = shortcode_to_id(shortcode)
        
        # 1-Manba: Instagram App API Info
        api_url = f"https://www.instagram.com/api/v1/media/{media_id}/info/"
        headers = {
            "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 480dpi; 1080x2400; Xiaomi; M2007J20CG; surya; qcom; en_US; 457476830)",
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*"
        }
        resp = requests.get(api_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            js = resp.json()
            items = js.get("items", [])
            if items:
                item = items[0]
                title = item.get("caption", {}).get("text", "Instagram Media") if item.get("caption") else "Instagram Media"
                
                carousel = item.get("carousel_media", [])
                if carousel and isinstance(carousel, list) and len(carousel) > 0:
                    media_list = []
                    for sub in carousel[:10]:
                        v_vers = sub.get("video_versions", [])
                        if v_vers:
                            media_list.append({"type": "video", "url": v_vers[0].get("url")})
                        else:
                            i_vers = sub.get("image_versions2", {}).get("candidates", [])
                            if i_vers:
                                media_list.append({"type": "photo", "url": i_vers[0].get("url")})
                    if media_list:
                        return {
                            "success": True,
                            "is_album": True,
                            "media_list": media_list,
                            "title": title[:50],
                            "is_audio": False,
                            "is_image": False,
                            "platform": "instagram"
                        }

                video_versions = item.get("video_versions", [])
                if video_versions:
                    return {
                        "success": True,
                        "direct_url": video_versions[0].get("url"),
                        "title": title[:50],
                        "is_audio": extract_audio,
                        "is_image": False,
                        "platform": "instagram"
                    }
                image_versions = item.get("image_versions2", {}).get("candidates", [])
                if image_versions:
                    return {
                        "success": True,
                        "direct_url": image_versions[0].get("url"),
                        "title": title[:50],
                        "is_audio": False,
                        "is_image": True,
                        "platform": "instagram"
                    }

        # 2-Manba: Direct Page HTML Parsing (Photo Posts & Karusel HD Extraction)
        clean_url = f"https://www.instagram.com/p/{shortcode}/"
        headers_web = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp2 = requests.get(clean_url, headers=headers_web, timeout=6)
        if resp2.status_code == 200:
            soup = BeautifulSoup(resp2.text, 'html.parser')
            title = soup.title.string.strip()[:50] if soup.title and soup.title.string else "Instagram Media"
            
            # HTML metadata search
            meta_imgs = soup.find_all("meta", property="og:image")
            meta_vids = soup.find_all("meta", property="og:video")
            
            if meta_vids:
                return {
                    "success": True,
                    "direct_url": meta_vids[0].get("content"),
                    "title": title,
                    "is_audio": False,
                    "is_image": False,
                    "platform": "instagram"
                }
                
            if meta_imgs:
                img_url = meta_imgs[0].get("content")
                return {
                    "success": True,
                    "direct_url": img_url,
                    "title": title,
                    "is_audio": False,
                    "is_image": True,
                    "platform": "instagram"
                }
    except Exception as e:
        logger.warning(f"Instagram fast error: {e}")
    return {"success": False}

def _fetch_pinterest_fast(url: str) -> dict:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string.strip()[:50] if soup.title and soup.title.string else "Pinterest Media"

            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if prop in ['og:video', 'og:video:secure_url', 'twitter:player:stream']:
                    content = meta.get('content')
                    if content and content.startswith('http'):
                        return {
                            "success": True,
                            "direct_url": content,
                            "title": title,
                            "is_audio": False,
                            "is_image": False,
                            "platform": "pinterest"
                        }

            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if prop in ['og:image', 'twitter:image']:
                    content = meta.get('content')
                    if content and content.startswith('http'):
                        if "pinimg.com" in content:
                            content = re.sub(r'/(?:736x|564x|474x|236x)/', '/originals/', content)
                        return {
                            "success": True,
                            "direct_url": content,
                            "title": title,
                            "is_audio": False,
                            "is_image": True,
                            "platform": "pinterest"
                        }
    except Exception as e:
        logger.warning(f"Pinterest fast error: {e}")
    return {"success": False}

def _fetch_youtube_fast(url: str, extract_audio: bool) -> dict:
    file_id = uuid.uuid4().hex[:8]
    out_template = str(DOWNLOADS_DIR / f"{file_id}_%(title).40s.%(ext)s")
    
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE,
        'noplaylist': True,
        'max_filesize': 49 * 1024 * 1024,
        'socket_timeout': 15,
        'extractor_args': {'youtube': ['player_client=android,web']}
    }
    
    if extract_audio:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]
    else:
        ydl_opts['format'] = 'bestvideo[height<=480][filesize<45M]+bestaudio/best[filesize<45M]/best[height<=360][filesize<45M]/worst'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                downloaded_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*"))
                if downloaded_files:
                    filepath = downloaded_files[0]
                    return {
                        "success": True,
                        "file_path": str(filepath),
                        "title": info.get('title', 'YouTube Video'),
                        "duration": info.get('duration', 0),
                        "is_audio": extract_audio or filepath.suffix.lower() in ['.mp3', '.m4a'],
                        "is_image": False,
                        "platform": "youtube"
                    }
    except Exception as e:
        logger.warning(f"YouTube compact download error: {e}")

    clean_id = re.sub(r'.*v=([^&]+).*', r'\1', url)
    y2_link = f"https://www.y2mate.com/youtube/{clean_id}"
    return {
        "success": True,
        "is_large": True,
        "title": "Katta Hajmdagi YouTube Video (2 soat+)",
        "duration": 7200,
        "direct_url": y2_link,
        "platform": "youtube"
    }

def _fetch_cobalt_public_api(url: str, extract_audio: bool) -> dict:
    try:
        api_url = "https://co.wuk.sh/api/json"
        payload = {"url": url, "isAudioOnly": extract_audio, "aFormat": "mp3"}
        headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        res = requests.post(api_url, json=payload, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            media_link = data.get("url")
            if media_link:
                return {
                    "success": True,
                    "direct_url": media_link,
                    "title": "Downloaded Media",
                    "duration": 0,
                    "is_audio": extract_audio,
                    "is_image": False,
                    "platform": detect_platform(url)
                }
    except Exception:
        pass
    return {"success": False}

def _fetch_ytdlp_fast(url: str, extract_audio: bool) -> dict:
    file_id = uuid.uuid4().hex[:8]
    out_template = str(DOWNLOADS_DIR / f"{file_id}_%(title).40s.%(ext)s")
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_EXE,
        'noplaylist': True,
        'max_filesize': 49 * 1024 * 1024,
        'concurrent_fragment_downloads': 8,
        'socket_timeout': 10,
        'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best/b'
    }
    if extract_audio:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
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
                        "is_audio": extract_audio or filepath.suffix.lower() in ['.mp3', '.m4a'],
                        "is_image": filepath.suffix.lower() in ['.jpg', '.png', '.webp'],
                        "platform": detect_platform(url)
                    }
    except Exception as e:
        logger.warning(f"yt-dlp fallback error: {e}")
    return {"success": False}

def _fetch_html_scrape(url: str) -> dict:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string.strip()[:50] if soup.title and soup.title.string else "Media"

            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if prop in ['og:video', 'og:video:secure_url', 'twitter:player:stream']:
                    content = meta.get('content')
                    if content and content.startswith('http'):
                        return {
                            "success": True,
                            "direct_url": content,
                            "title": title,
                            "is_audio": False,
                            "is_image": False,
                            "platform": detect_platform(url)
                        }

            for meta in soup.find_all('meta'):
                prop = meta.get('property', '') or meta.get('name', '')
                if prop in ['og:image', 'twitter:image']:
                    content = meta.get('content')
                    if content and content.startswith('http'):
                        return {
                            "success": True,
                            "direct_url": content,
                            "title": title,
                            "is_audio": False,
                            "is_image": True,
                            "platform": detect_platform(url)
                        }
    except Exception:
        pass
    return {"success": False}
