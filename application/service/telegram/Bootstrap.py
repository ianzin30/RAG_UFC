"""Bootstrap helpers for the Telegram bot."""
# Simple: Start the Telegram bot and register commands

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from .Handlers import clear, extractor, handle_chat, login, start


# Esta fabrica registra todos os comandos e handlers do bot em um unico ponto.
def build_bot_application(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("extractor", extractor))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))
    return app
