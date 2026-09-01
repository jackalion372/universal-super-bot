import os
from pathlib import Path
from dotenv import load_dotenv
from core.logger import logger

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
TEMP_DIR = DATA_DIR / "temp"
DB_PATH = DATA_DIR / "bot_database.db"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8865054491:AAE9zV7eAblAyflmz5O_UqAj35LfapAcW04"
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS") or "7839115738"
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")




# Limitlar
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
AUTO_CLEANUP_MINUTES = int(os.getenv("AUTO_CLEANUP_MINUTES", "30"))
