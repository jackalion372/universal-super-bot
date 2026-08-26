import os
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
            # Fallback transparency for high contrast
            img = Image.open(input_path).convert("RGBA")
            datas = img.getdata()
            newData = []
            for item in datas:
                # White background cutout
                if item[0] > 220 and item[1] > 220 and item[2] > 220:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            img.putdata(newData)
            img.save(output_path, "PNG")
            return True
        except Exception:
            return False

def compress_image(input_path: str, output_path: str, quality: int = 50) -> bool:
    try:
        img = Image.open(input_path)
        img.save(output_path, optimize=True, quality=quality)
        return True
    except Exception as e:
        logger.error(f"Compress image error: {e}")
        return False

def compress_video(input_path: str, output_path: str) -> bool:
    try:
        cmd = [
            FFMPEG_EXE, "-y", "-i", input_path,
            "-vcodec", "libx264", "-crf", "28", "-preset", "faster",
            "-acodec", "aac", "-b:a", "128k",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Video compress error: {e}")
        return False

async def extract_text_from_image(user_id: int, image_path: str) -> str:
    prompt = """
Ushbu rasmdagi barcha yozuv va matnlarni (OCR) hech qanday o'zgartirishsiz, to'g'ri va aniq ajratib bering.
Faqat rasmdagi matnni qaytaring, ortiqcha izohsiz.
"""
    return await analyze_image_with_ai(user_id, image_path, prompt)

def video_to_mp3(video_path: str, audio_path: str) -> bool:
    try:
        cmd = [
            FFMPEG_EXE, "-y", "-i", video_path,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            audio_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(audio_path)
    except Exception as e:
        logger.error(f"Video to MP3 error: {e}")
        return False
