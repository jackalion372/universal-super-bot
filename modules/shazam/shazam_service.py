import os
import asyncio
import subprocess
import uuid
from pathlib import Path
from shazamio import Shazam
import yt_dlp
import imageio_ffmpeg
from core.config import TEMP_DIR, DOWNLOADS_DIR, logger

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
shazam = Shazam()

async def recognize_song_from_file(file_path: str) -> dict:
    converted_path = str(TEMP_DIR / f"converted_{uuid.uuid4().hex[:8]}.mp3")
    try:
        # Convert any input audio/video/voice into clean 44.1kHz MP3 using FFmpeg
        cmd = [
            FFMPEG_EXE, "-y", "-i", file_path,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            converted_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        target_audio = converted_path if os.path.exists(converted_path) else file_path
        out = await shazam.recognize(target_audio)
        track = out.get('track', {})
        if not track:
            return {"success": False, "message": "Qo'shiq topilmadi"}
        
        title = track.get('title', "Noma'lum")
        subtitle = track.get('subtitle', "Noma'lum ijrochi")
        genres = track.get('genres', {}).get('primary', '')
        cover_art = track.get('images', {}).get('coverart', '')
        
        lyrics = []
        for section in track.get('sections', []):
            if section.get('type') == 'LYRICS':
                lyrics = section.get('text', [])
                break
                
        return {
            "success": True,
            "title": title,
            "artist": subtitle,
            "genre": genres,
            "cover_art": cover_art,
            "lyrics": "\n".join(lyrics) if lyrics else None,
            "query": f"{subtitle} - {title}"
        }
    except Exception as e:
        logger.error(f"Shazam recognition error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if os.path.exists(converted_path):
            try:
                os.remove(converted_path)
            except OSError:
                pass

async def search_and_download_music(query: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_music_search_and_download, query)

def _sync_music_search_and_download(query: str) -> dict:
    file_id = uuid.uuid4().hex[:8]
    out_template = str(DOWNLOADS_DIR / f"{file_id}_%(title).50s.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'ffmpeg_location': FFMPEG_EXE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
            else:
                entry = info
            
            title = entry.get('title', query)
            duration = entry.get('duration', 0)
            
            target_files = list(DOWNLOADS_DIR.glob(f"{file_id}_*.mp3"))
            if not target_files:
                return {"success": False, "error": "Musiqa yuklanmadi"}
            
            return {
                "success": True,
                "file_path": str(target_files[0]),
                "title": title,
                "duration": duration,
                "artist": entry.get('uploader', "Artist")
            }
    except Exception as e:
        logger.error(f"Music search/download error for {query}: {e}")
        return {"success": False, "error": str(e)}
