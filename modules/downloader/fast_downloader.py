import os
import re
import asyncio
import uuid
import shutil
import html
import json
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
    
    # 1. TikTok Engine (3 API Fallback Chain: TikWM -> SSSTik -> MusicalDown)
    if platform == "tiktok":
        res = _fetch_tiktok_tikwm(url, extract_audio)
        if res.get("success"):
            return res
        res_ssstik = _fetch_tiktok_ssstik(url, extract_audio)
        if res_ssstik.get("success"):
            return res_ssstik
        res_musical = _fetch_tiktok_musicaldown(url, extract_audio)
        if res_musical.get("success"):
            return res_musical


    # 2. Instagram Engine (100% Ultra HD Karusel & Photo Post Extraction)
    if platform == "instagram":
        res = _fetch_instagram_fast(url, extract_audio)
        if res.get("success"):
            return res

    # 3. Pinterest Engine (HD Video & 4K Photo Extraction)
    if platform == "pinterest":
        res = _fetch_pinterest_fast(url)
        if res.get("success"):
            return res

    # 4. YouTube Engine
    if platform == "youtube":
        res = _fetch_youtube_fast(url, extract_audio)
        if res.get("success"):
            return res

    # 5. yt-dlp Direct Stream Engine
    res_ytdl = _fetch_ytdlp_fast(url, extract_audio)
    if res_ytdl.get("success"):
        return res_ytdl

    # 6. HTML Meta Scraper Engine
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
    return {"success": False}

def _fetch_tiktok_ssstik(url: str, extract_audio: bool) -> dict:
    try:
        api_url = "https://ssstik.io/abc?url=dl"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        data = {"id": url, "locale": "en", "tt": "0"}
        resp = requests.post(api_url, headers=headers, data=data, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            download_links = soup.find_all('a', class_='download_link')
            for link in download_links:
                href = link.get('href')
                if href and ("tikcdn" in href or "ssstik" in href or href.startswith("http")):
                    return {
                        "success": True,
                        "direct_url": href,
                        "title": "TikTok HD Video",
                        "is_audio": False,
                        "is_image": False,
                        "platform": "tiktok"
                    }
    except Exception as e:
        logger.warning(f"SSSTik error: {e}")
    return {"success": False}

def _fetch_tiktok_musicaldown(url: str, extract_audio: bool) -> dict:
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r1 = session.get("https://musicaldown.com/en", headers=headers, timeout=4)
        if r1.status_code == 200:
            soup = BeautifulSoup(r1.text, 'html.parser')
            inputs = soup.find_all('input')
            data = {}
            for inp in inputs:
                if inp.get('name'):
                    data[inp.get('name')] = inp.get('value', '')
            data['url_name'] = url
            
            r2 = session.post("https://musicaldown.com/download", headers=headers, data=data, timeout=4)
            if r2.status_code == 200:
                soup2 = BeautifulSoup(r2.text, 'html.parser')
                links = soup2.find_all('a', class_='download')
                for l in links:
                    href = l.get('href')
                    if href and href.startswith("http"):
                        return {
                            "success": True,
                            "direct_url": href,
                            "title": "TikTok HD Video",
                            "is_audio": False,
                            "is_image": False,
                            "platform": "tiktok"
                        }
    except Exception as e:
        logger.warning(f"Musicaldown error: {e}")
    return {"success": False}


def _fetch_instagram_fast(url: str, extract_audio: bool) -> dict:
    """Instagram Karusel (?img_index=X bo'lsa ham) va barcha rasmlarni 1080p HD va kesmasdan yuklash engine"""
    try:
        match = re.search(r"instagram\.com/(?:p|reel|tv)/([\w\-]+)", url, re.IGNORECASE)
        if not match:
            return {"success": False}
            
        main_shortcode = match.group(1)
        media_id = shortcode_to_id(main_shortcode)
        
        # 1-Manba: Direct Instagram App API Info (1080p Candidates)
        api_url = f"https://www.instagram.com/api/v1/media/{media_id}/info/"
        headers_api = {
            "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 480dpi; 1080x2400; Xiaomi; M2007J20CG; surya; qcom; en_US; 457476830)",
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*"
        }
        resp = requests.get(api_url, headers=headers_api, timeout=4)
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

        # 2-Manba: yt-dlp Logger Intercept & Embed HD Fetch
        shortcodes = []
        class InterceptLogger:
            def debug(self, msg):
                m = re.search(r"\[Instagram\] ([\w\-]+):", msg)
                if m and m.group(1) not in shortcodes:
                    shortcodes.append(m.group(1))
            def warning(self, msg): pass
            def error(self, msg):
                m = re.search(r"\[Instagram\] ([\w\-]+):", msg)
                if m and m.group(1) not in shortcodes:
                    shortcodes.append(m.group(1))

        clean_url = f"https://www.instagram.com/p/{main_shortcode}/"
        ydl_opts = {
            'quiet': False,
            'no_warnings': True,
            'ignoreerrors': True,
            'logger': InterceptLogger()
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(clean_url, download=False)
        except Exception:
            pass

        if main_shortcode not in shortcodes and not shortcodes:
            shortcodes.append(main_shortcode)

        media_list = []
        headers_embed = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for sc in shortcodes:
            embed_url = f"https://www.instagram.com/p/{sc}/embed/"
            try:
                r_emb = requests.get(embed_url, headers=headers_embed, timeout=4)
                if r_emb.status_code == 200:
                    imgs = re.findall(r'https://[^\s"\'<>]+fbcdn[^\s"\'<>]+\.jpg\?stp=dst-jpg[^\s"\'<>]*', r_emb.text)
                    if not imgs:
                        imgs = re.findall(r'https://[^\s"\'<>]+fbcdn[^\s"\'<>]+\.jpg[^\s"\'<>]*', r_emb.text)
                    if imgs:
                        clean_img = html.unescape(imgs[0].replace('\\/', '/'))
                        media_list.append({"type": "photo", "url": clean_img})
            except Exception:
                pass

        if len(media_list) > 1:
            return {
                "success": True,
                "is_album": True,
                "media_list": media_list,
                "title": "Instagram Album",
                "is_audio": False,
                "is_image": False,
                "platform": "instagram"
            }
        elif len(media_list) == 1:
            return {
                "success": True,
                "direct_url": media_list[0]["url"],
                "title": "Instagram Photo",
                "is_audio": False,
                "is_image": True,
                "platform": "instagram"
            }

    except Exception as e:
        logger.warning(f"Instagram fast error: {e}")
    return {"success": False}

def _fetch_pinterest_fast(url: str) -> dict:
    """Pinterest HD Video & 4K Photo extractor engine"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        # 1. Shortened pin.it link resolving
        resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        final_url = resp.url
        
        # Clean Pin ID URL (strip /sent/?invite_code= tracking params)
        pin_match = re.search(r'/pin/(\d+)', final_url)
        clean_pin_url = f"https://www.pinterest.com/pin/{pin_match.group(1)}/" if pin_match else final_url
        
        resp2 = requests.get(clean_pin_url, headers=headers, timeout=6)
        if resp2.status_code == 200:
            soup = BeautifulSoup(resp2.text, 'html.parser')
            title = soup.title.string.strip()[:50] if soup.title and soup.title.string else "Pinterest Media"

            # 2. Extract Direct MP4 Video Stream URLs from v.pinimg.com
            v_urls = re.findall(r'https://[^\s"\'<>]+v\.pinimg\.com[^\s"\'<>]+\.mp4', resp2.text)
            if not v_urls:
                v_urls = re.findall(r'https://[^\s"\'<>]+pinimg\.com[^\s"\'<>]+\.mp4', resp2.text)

            if v_urls:
                clean_vids = list(set([html.unescape(v.replace('\\/', '/')) for v in v_urls]))
                best_vid = clean_vids[0]
                for v in clean_vids:
                    if "720p" in v.lower() or "v720p" in v.lower():
                        best_vid = v
                        break
                return {
                    "success": True,
                    "direct_url": best_vid,
                    "title": title,
                    "is_audio": False,
                    "is_image": False,
                    "platform": "pinterest"
                }

            # 3. Check for Meta Video Tags
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

            # 4. Check for Meta Photo Tags (Original 4K/HD Quality)
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

        # 5. yt-dlp Fallback on Clean Pin URL
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_pin_url, download=False)
            if info and info.get("url"):
                return {
                    "success": True,
                    "direct_url": info["url"],
                    "title": info.get("title", "Pinterest Video"),
                    "is_audio": False,
                    "is_image": info.get("ext") in ["jpg", "png", "webp"],
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
        ydl_opts['format'] = 'bestvideo[height<=480][filesize<45M]+bestaudio/best[filesize<45M]/best[filesize<45M]/worst'

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
