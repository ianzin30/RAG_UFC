import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from .bot_runtime.bootstrap import build_bot_application
except ImportError:
    from bot_runtime.bootstrap import build_bot_application


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def main() -> None:
    if not TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env file.")

    app = build_bot_application(TOKEN)
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
