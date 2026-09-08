import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

DB_PATH = "moderation.db"

ADMIN_ROLES = ["creator", "administrator"]

DEFAULT_SETTINGS = {
    "welcome_enabled": True,
    "welcome_message": "Добро пожаловать, {user}! Ты {count}-й участник чата.",
    "antiflood_enabled": True,
    "antiflood_limit": 5,
    "antiflood_timeout": 10,
    "log_enabled": True,
    "log_chat": None,
}

BAN_WORDS = []
MUTE_WORDS = []
WARN_LIMIT = 3
