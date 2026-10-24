import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "tickets.db")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ---------- Вспомогательное ----------
def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "y", "on")

# ---------- Прокси ----------
USE_PROXY  = _env_bool("USE_PROXY", False)
PROXY_TYPE = os.getenv("PROXY_TYPE", "socks5h")   # socks5h / socks5 / http / https
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = os.getenv("PROXY_PORT", "10808")

def get_proxy_config() -> dict | None:
    """Возвращает словарь для telebot.apihelper.proxy или None, если прокси выключен."""
    if not USE_PROXY:
        return None
    url = f"{PROXY_TYPE}://{PROXY_HOST}:{PROXY_PORT}"
    return {"https": url, "http": url}


CATEGORIES = {
    "concert": "🎵 Концерты",
    "movie":   "🎬 Фильмы",
    "theater": "🎭 Спектакли",
    "tasting": "🍷 Дегустации",
}

STATUS_EMOJI = {
    "pending":   "⏳ ожидает подтверждения",
    "confirmed": "✅ подтверждена",
    "cancelled": "❌ отменена",
}

PAYMENT_LABEL = {"online": "💳 Онлайн", "cash": "💵 Наличными"}