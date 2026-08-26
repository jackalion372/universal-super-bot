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

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Limitlar
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
AUTO_CLEANUP_MINUTES = int(os.getenv("AUTO_CLEANUP_MINUTES", "30"))
