import os

try:
    from .runtime_config import load_project_environment
    from .bot_runtime.bootstrap import build_bot_application
except ImportError:
    from runtime_config import load_project_environment
    from bot_runtime.bootstrap import build_bot_application

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
