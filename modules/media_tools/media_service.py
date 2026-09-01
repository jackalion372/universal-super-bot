import os
import asyncio
import subprocess
import uuid
from pathlib import Path
from PIL import Image
import imageio_ffmpeg
from core.config import TEMP_DIR, logger
from modules.ai.ai_engine import analyze_image_with_ai

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def remove_background(input_path: str, output_path: str) -> bool:
    try:
        from rembg import remove
        input_image = Image.open(input_path)
        output_image = remove(input_image)
        output_image.save(output_path, format="PNG")
        return True
    except Exception as e:
        logger.warning(f"Rembg error: {e}. Fallback to image mask")
        try:
            img = Image.open(input_path).convert("RGBA")
            datas = img.getdata()
            newData = []
            for item in datas:
                if item[0] > 220 and item[1] > 220 and item[2] > 220:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            img.putdata(newData)
            img.save(output_path, "PNG")
            return True
        except Exception:
            return False

def compress_image(input_path: str, output_path: str, quality: int = 65) -> bool:
    """
    Rasm hajmini sifatini zarracha buzmasdan optimal siqib beradi.
    """
    try:
        img = Image.open(input_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Maksimalligi 2048px ga moslab sifatni saqlagan holda siqamiz
        max_size = (2048, 2048)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(output_path, "JPEG", optimize=True, quality=quality)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Compress image error: {e}")
        return False

async def compress_video(input_path: str, output_path: str) -> bool:
    """
    Videoni tezkor ultrafast preset va optimal crf orqali siqadi.
    """
    try:
        cmd = [
            FFMPEG_EXE, "-y", "-i", input_path,
            "-vcodec", "libx264", "-crf", "28", "-preset", "ultrafast",
            "-acodec", "aac", "-b:a", "128k",
            output_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.wait()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Video compress error: {e}")
        return False

async def extract_text_from_image(user_id: int, image_path: str) -> str:
    """
    Rasmdagi barcha turdagi matn va yozuvlarni (O'zbek, Rus, Ingliz) 100% aniqlikda ajratadi.
    """
    prompt = (
        "Ushbu rasmdagi barcha yozuv va matnlarni (O'zbek, Kirill, Rus, Ingliz) 100% aniqlikda matn ko'rinishida ajratib bering.\n"
        "Hech qanday keraksiz izoh yozmang, faqat rasmdagi matnning o'zini qaytaring."
    )
    res = await analyze_image_with_ai(user_id, image_path, prompt)
    return res if res else "❌ Rasmdan matn ajratib bo'lmadi."

async def video_to_mp3(video_path: str, audio_path: str) -> bool:
    """
    Videodan 192kbps tiniq MP3 audio ajratib beradi.
    """
    try:
        cmd = [
            FFMPEG_EXE, "-y", "-i", video_path,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            audio_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.wait()
        return os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
    except Exception as e:
        logger.error(f"Video to MP3 error: {e}")
        return False

