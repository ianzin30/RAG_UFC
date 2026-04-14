"""Onboarding helpers for extraction and login prompts."""

from telegram import Update
from telegram.ext import ContextTypes

from .replies import reply
from .session import ensure_session, reset_loaded_collection

try:
    from ..bot_support.drive_chat import build_login_intro_messages
    from ..bot_support.extraction_selection import (
        build_extraction_choice_prompt,
        build_extraction_selected_message,
        build_invalid_extraction_choice_message,
        normalize_extraction_method,
    )
except ImportError:
    from bot_support.drive_chat import build_login_intro_messages
    from bot_support.extraction_selection import (
        build_extraction_choice_prompt,
        build_extraction_selected_message,
        build_invalid_extraction_choice_message,
        normalize_extraction_method,
    )


# Esta mensagem pede a escolha inicial do extrator quando ainda nao existe sessao pronta.
async def send_extraction_choice_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = ensure_session(context)
    session["awaiting_extraction_choice"] = True
    await reply(update, build_extraction_choice_prompt())


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


# Esta etapa valida a escolha do extrator e reposiciona o fluxo do onboarding.
async def handle_extraction_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    choice_text: str,
) -> bool:
    session = ensure_session(context)
    selected_method = normalize_extraction_method(choice_text)

    if selected_method:
        reset_loaded_collection(session)
        session["extraction_method"] = selected_method
        session["awaiting_extraction_choice"] = False
        await reply(update, build_extraction_selected_message(selected_method))
        await send_login_intro(update, context)
        return True

    if session["awaiting_extraction_choice"]:
        await reply(update, build_invalid_extraction_choice_message())
        return True
    return False
