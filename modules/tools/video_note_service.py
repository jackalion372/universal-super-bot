import os
import re
import uuid
import asyncio
import subprocess
from pathlib import Path
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

from core.config import TEMP_DIR, logger

def get_video_duration(input_path: str) -> float:
    """
    FFmpeg orqali video davomiyligini (soniyada) aniqlaydi.
    """
    cmd = [FFMPEG_EXE, "-i", input_path]
    try:
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        _, stderr = proc.communicate(timeout=5)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", stderr)
        if match:
            hours, minutes, seconds = match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except Exception as e:
        logger.error(f"Duration probe error: {e}")
    return 30.0

async def convert_video_to_round_note_with_progress(input_path: str, progress_callback=None) -> str:
    """
    Istalgan videoni 2-3 soniyada ultra-tezkor Telegram 1:1 Dumaloq Video Note'ga o'tkazadi
    va % ko'rsatkichli progress bar uzatadi.
    """
    output_path = str(TEMP_DIR / f"vnote_{uuid.uuid4().hex[:8]}.mp4")
    total_duration = get_video_duration(input_path)
    if total_duration <= 0:
        total_duration = 30.0

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", input_path,
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))/2:(ih-min(iw\\,ih))/2,scale='min(720,min(iw,ih))':'min(720,min(iw,ih))'",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-crf", "24",
        "-threads", "0",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", "60",
        "-progress", "pipe:1",
        output_path
    ]




    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )

        last_percent = -1
        last_update_time = 0

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='ignore').strip()
            
            if line_str.startswith("out_time_us="):
                try:
                    us = int(line_str.split("=")[1])
                    curr_sec = us / 1_000_000.0
                    percent = min(99, int((curr_sec / total_duration) * 100))
                    
                    now = asyncio.get_event_loop().time()
                    if percent != last_percent and (now - last_update_time >= 0.7 or percent == 99):
                        last_percent = percent
                        last_update_time = now
                        if progress_callback:
                            await progress_callback(percent)
                except Exception:
                    pass

        await proc.wait()

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if progress_callback:
                await progress_callback(100)
            return output_path
    except Exception as e:
        logger.error(f"Video note conversion error: {e}")

    return None
