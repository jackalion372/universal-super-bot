import os
import uuid
import asyncio
import subprocess
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

from core.config import TEMP_DIR, logger

async def convert_video_to_round_note(input_path: str) -> str:
    """
    Istalgan oddiy videoni 1:1 kvadrat Telegram Dumaloq Video Note (video message) formatiga o'tkazadi.
    """
    output_path = str(TEMP_DIR / f"vnote_{uuid.uuid4().hex[:8]}.mp4")
    
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", input_path,
        "-vf", "crop=ih:ih,scale=480:480",
        "-c:v", "libx264",
        "-crf", "26",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", "60",
        output_path
    ]

    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.wait()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
    except Exception as e:
        logger.error(f"Video note conversion error: {e}")
        
    return None
