"""Telegram bot entry point.

Initializes the environment, loads configuration, and starts the Telegram bot
application with the token from .env.
"""
import os

try:
    from .RuntimeConfig import load_project_environment
    from .telegram.Bootstrap import build_bot_application
except ImportError:
    from RuntimeConfig import load_project_environment
    from telegram.Bootstrap import build_bot_application

load_project_environment()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env file.")

    app = build_bot_application(TOKEN)
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
