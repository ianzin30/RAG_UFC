"""Session helpers for the Telegram bot."""
# Simple: Store user data and chat history

from telegram import Update
from telegram.ext import ContextTypes

from .RouteSession import clear_collection_session, ensure_collection_session
from .ExtractionSelection import ensure_extraction_session


# Este helper garante que a sessao tenha todas as chaves esperadas pelo bot.
def ensure_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    session = context.user_data
    session.setdefault("collection", None)
    session.setdefault("files_count", 0)
    session.setdefault("messages", [])
    session.setdefault("rag_service", None)
    session.setdefault("login_in_progress", False)
    session.setdefault("loading_in_progress", False)
    ensure_collection_session(session)
    return ensure_extraction_session(session)


# Este helper monta uma saudacao simples a partir do nome exibido pelo Telegram.
def display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "!"
    return f", {user.first_name}" if user.first_name else ""


# Este reset limpa a colecao carregada quando o fluxo precisa recomeçar.
def reset_loaded_collection(session: dict) -> None:
    session["collection"] = None
    session["files_count"] = 0
    session["messages"] = []
    session["rag_service"] = None
    clear_collection_session(session)
