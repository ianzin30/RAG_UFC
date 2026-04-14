"""Constants for local chat session storage."""

from pathlib import Path


DEFAULT_CHAT_TITLE = "Nova conversa"
MAX_CHAT_SESSIONS = 3
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHAT_STORAGE_PATH = PROJECT_ROOT / "data" / "local_chat_sessions.json"
