"""Reply helpers for the Telegram bot."""
# Simple: Send messages back to Telegram users

from telegram import Update


async def reply(update: Update, text: str) -> None:
    if not update.message:
        return
    await update.message.reply_text(text, do_quote=True)


async def reply_animation(update: Update, animation_url: str, caption: str) -> None:
    if not update.message:
        return
    await update.message.reply_animation(animation=animation_url, caption=caption, do_quote=True)
