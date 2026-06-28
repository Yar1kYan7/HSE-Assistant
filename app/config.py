import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен в переменных окружения")

GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
if not GOOGLE_SHEETS_URL:
    raise ValueError("GOOGLE_SHEETS_URL не установлен в переменных окружения")

ADMIN_TG = int(os.getenv("ADMIN_TG", "0")) or None
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")