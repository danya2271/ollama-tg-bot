# --- Configuration ---
# It is recommended to use environment variables for sensitive data like your Telegram token.
import os

OLLAMA_GUEST_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")
