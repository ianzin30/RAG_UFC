"""Onboarding helpers for extraction and login prompts."""

from telegram import Update
from telegram.ext import ContextTypes

from .replies import reply
from .session import ensure_session, reset_loaded_collection

try:
    from ..bot_support.drive_chat import build_login_intro_messages
    from ..bot_support.extraction_selection import (
        build_extraction_selected_message,
        EXTRACTION_METHOD_DOCLING,
        normalize_extraction_method,
    )
except ImportError:
    from bot_support.drive_chat import build_login_intro_messages
    from bot_support.extraction_selection import (
        build_extraction_selected_message,
        EXTRACTION_METHOD_DOCLING,
        normalize_extraction_method,
    )


# Este helper fixa Docling como extrator do Google Drive e avanca para o login.
async def send_extraction_choice_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = ensure_session(context)
    previous_method = session.get("extraction_method")
    session["extraction_method"] = EXTRACTION_METHOD_DOCLING
    session["awaiting_extraction_choice"] = False
    if previous_method != EXTRACTION_METHOD_DOCLING:
        await reply(update, build_extraction_selected_message(EXTRACTION_METHOD_DOCLING))
    await send_login_intro(update, context)


# Esta introducao explica o proximo passo do login de acordo com o extrator escolhido.
async def send_login_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = ensure_session(context)
    extraction_method = session.get("extraction_method")
    if not extraction_method:
        await send_extraction_choice_prompt(update, context)
        return

    intro, details = build_login_intro_messages(extraction_method)
    await reply(update, intro)
    await reply(update, details)


# Esta etapa mantem compatibilidade com mensagens antigas, mas sempre fixa Docling.
async def handle_extraction_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    choice_text: str,
) -> bool:
    session = ensure_session(context)
    selected_method = normalize_extraction_method(choice_text)

    if selected_method or session["awaiting_extraction_choice"]:
        reset_loaded_collection(session)
        session["extraction_method"] = EXTRACTION_METHOD_DOCLING
        session["awaiting_extraction_choice"] = False
        await reply(update, build_extraction_selected_message(EXTRACTION_METHOD_DOCLING))
        await send_login_intro(update, context)
        return True
    return False
