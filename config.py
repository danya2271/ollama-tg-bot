# --- Configuration ---
# It is recommended to use environment variables for sensitive data like your Telegram token.
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")
ALLOWED_TELEGRAM_USER_IDS = [int(user_id) for user_id in os.getenv("ALLOWED_TELEGRAM_USER_IDS", "123456789").split(",")]
