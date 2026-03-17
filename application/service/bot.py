import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

try:
    from .bot_support.collection_route import (
        build_collection_route_response,
        clear_collection_session,
        ensure_collection_session,
        update_collection_session,
    )
    from .bot_support.drive_chat import (
        DRIVE_FOLDER_NAME,
        build_login_intro_messages,
        build_ready_message,
        build_success_caption,
        login_google_drive,
        prepare_chat_from_drive,
    )
    from .bot_support.extraction_selection import (
        build_extraction_choice_prompt,
        build_extraction_selected_message,
        build_invalid_extraction_choice_message,
        ensure_extraction_session,
        normalize_extraction_method,
    )
except ImportError:
    from bot_support.collection_route import (
        build_collection_route_response,
        clear_collection_session,
        ensure_collection_session,
        update_collection_session,
    )
    from bot_support.drive_chat import (
        DRIVE_FOLDER_NAME,
        build_login_intro_messages,
        build_ready_message,
        build_success_caption,
        login_google_drive,
        prepare_chat_from_drive,
    )
    from bot_support.extraction_selection import (
        build_extraction_choice_prompt,
        build_extraction_selected_message,
        build_invalid_extraction_choice_message,
        ensure_extraction_session,
        normalize_extraction_method,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUCCESS_GIF_URL = "https://media1.tenor.com/m/gvjH24AtYM0AAAAC/minion-minions.gif"


def _ensure_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    session = context.user_data
    session.setdefault("collection", None)
    session.setdefault("files_count", 0)
    session.setdefault("messages", [])
    session.setdefault("rag_service", None)
    session.setdefault("login_in_progress", False)
    session.setdefault("loading_in_progress", False)
    ensure_collection_session(session)
    return ensure_extraction_session(session)


def _display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "!"

    return f", {user.first_name}" if user.first_name else ""


async def _reply(update: Update, text: str) -> None:
    if not update.message:
        return

    await update.message.reply_text(text, do_quote=True)


async def _reply_animation(update: Update, animation_url: str, caption: str) -> None:
    if not update.message:
        return

    await update.message.reply_animation(animation=animation_url, caption=caption, do_quote=True)


def _reset_loaded_collection(session: dict) -> None:
    session["collection"] = None
    session["files_count"] = 0
    session["messages"] = []
    session["rag_service"] = None
    clear_collection_session(session)


async def _send_extraction_choice_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = _ensure_session(context)
    session["awaiting_extraction_choice"] = True
    await _reply(update, build_extraction_choice_prompt())


async def _send_login_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = _ensure_session(context)
    extraction_method = session.get("extraction_method")
    if not extraction_method:
        await _send_extraction_choice_prompt(update, context)
        return

    intro, details = build_login_intro_messages(extraction_method)
    await _reply(update, intro)
    await _reply(update, details)


async def _handle_extraction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, choice_text: str) -> bool:
    session = _ensure_session(context)
    selected_method = normalize_extraction_method(choice_text)

    if selected_method:
        _reset_loaded_collection(session)
        session["extraction_method"] = selected_method
        session["awaiting_extraction_choice"] = False
        await _reply(update, build_extraction_selected_message(selected_method))
        await _send_login_intro(update, context)
        return True

    if session["awaiting_extraction_choice"]:
        await _reply(update, build_invalid_extraction_choice_message())
        return True

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = _ensure_session(context)
    if session["rag_service"] is not None and session["collection"]:
        await _reply(update, build_ready_message(session["files_count"], session["extraction_method"]))
        return

    if session["login_in_progress"] or session["loading_in_progress"]:
        await _reply(
            update,
            "Já estou preparando o acesso aos seus documentos.\n"
            "Aguarde mais alguns instantes e eu aviso quando tudo estiver pronto.",
        )
        return

    await _reply(
        update,
        f"Olá{_display_name(update)}, tudo bem? 👋\n\n"
        "Estou aqui para te ajudar com os seus documentos ✨",
    )
    if session["extraction_method"]:
        await _send_login_intro(update, context)
        return

    await _send_extraction_choice_prompt(update, context)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    session = _ensure_session(context)
    if not session["extraction_method"]:
        await _send_extraction_choice_prompt(update, context)
        return

    if session["login_in_progress"] or session["loading_in_progress"]:
        await _reply(
            update,
            "A preparação já está em andamento.\n"
            "Conclua a autenticação no navegador, se ela ainda estiver aberta, e aguarde mais alguns instantes.",
        )
        return

    session["login_in_progress"] = True
    await _reply(
        update,
        "🔓 Vou abrir o login do Google Drive no navegador desta máquina.\n\n"
        f"✅ Entre com sua conta e autorize o acesso para que eu importe os arquivos compatíveis da pasta '{DRIVE_FOLDER_NAME}'.",
    )

    try:
        drive_service, credentials = await asyncio.to_thread(login_google_drive)
    except Exception as exc:
        await _reply(update, f"Não foi possível concluir a conexão com o Google Drive: {exc}")
        session["login_in_progress"] = False
        return

    session["login_in_progress"] = False
    session["loading_in_progress"] = True

    await _reply(
        update,
        "✅ Conexão com o Google Drive concluída com sucesso.\n\n"
        "⏳ Agora vou importar e preparar os arquivos para o chat.\n"
        "Isso pode levar alguns segundos.",
    )

    try:
        result, rag_service = await asyncio.to_thread(
            prepare_chat_from_drive,
            update.effective_user.id,
            drive_service,
            credentials,
            session["extraction_method"],
        )
    except Exception as exc:
        await _reply(update, f"Não foi possível carregar os arquivos do Google Drive: {exc}")
    else:
        files_count = len(result.get("files", []))
        session["collection"] = result["collection_name"]
        session["files_count"] = files_count
        session["messages"] = []
        session["rag_service"] = rag_service
        session["extraction_method"] = result["extraction_method"]
        session["awaiting_extraction_choice"] = False
        update_collection_session(session, result)

        success_caption = build_success_caption(
            files_count,
            result["folder_name"],
            result["extraction_method"],
        )

        try:
            await _reply_animation(update, SUCCESS_GIF_URL, success_caption)
        except Exception:
            await _reply(
                update,
                success_caption,
            )
    finally:
        session["login_in_progress"] = False
        session["loading_in_progress"] = False


async def extractor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = _ensure_session(context)
    if session["login_in_progress"] or session["loading_in_progress"]:
        await _reply(
            update,
            "Ainda estou processando a importação atual.\n"
            "Aguarde terminar para trocar o extrator.",
        )
        return

    _reset_loaded_collection(session)
    session["extraction_method"] = None
    session["awaiting_extraction_choice"] = False
    await _send_extraction_choice_prompt(update, context)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = _ensure_session(context)
    session["messages"] = []
    await _reply(
        update,
        "Pronto.\n"
        "Limpei o histórico da conversa. Pode enviar uma nova pergunta quando quiser.",
    )


async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    session = _ensure_session(context)
    if session["awaiting_extraction_choice"]:
        handled = await _handle_extraction_choice(update, context, update.message.text)
        if handled:
            return

    if session["login_in_progress"]:
        await _reply(
            update,
            "Ainda estou aguardando a conclusão do login no Google Drive.\n"
            "Termine a autenticação no navegador e tente novamente em seguida.",
        )
        return

    if session["loading_in_progress"]:
        await _reply(
            update,
            "A conexão com o Google Drive já foi concluída.\n"
            "Agora ainda estou carregando os arquivos e preparando o chat.\n"
            "Aguarde mais alguns segundos.",
        )
        return

    if session["rag_service"] is None:
        if not session["extraction_method"]:
            handled = await _handle_extraction_choice(update, context, update.message.text)
            if handled:
                return
            await _send_extraction_choice_prompt(update, context)
            return

        await _send_login_intro(update, context)
        return

    question = update.message.text.strip()
    recent_history = session["messages"][-6:]
    session["messages"].append({"role": "user", "content": question})

    direct_answer = build_collection_route_response(question, session)
    if direct_answer is not None:
        session["messages"].append({"role": "assistant", "content": direct_answer})
        await _reply(update, direct_answer)
        return

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        answer = await asyncio.to_thread(session["rag_service"].ask_question, question, recent_history)
    except Exception as exc:
        answer = f"Erro ao obter resposta: {exc}"

    session["messages"].append({"role": "assistant", "content": answer})
    await _reply(update, answer)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env file.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("extractor", extractor))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
