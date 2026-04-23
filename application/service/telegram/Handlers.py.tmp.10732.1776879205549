"""Command and chat handlers for the Telegram bot."""
# Simple: Process user messages and commands

import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from .Onboarding import handle_extraction_choice, send_extraction_choice_prompt, send_login_intro
from .Replies import reply, reply_animation
from .Session import display_name, ensure_session, reset_loaded_collection
from .RouteResponses import build_collection_route_response
from .RouteSession import update_collection_session
from .DriveChat import (
    DRIVE_FOLDER_NAME,
    build_ready_message,
    build_success_caption,
    login_google_drive,
    prepare_chat_from_drive,
)


SUCCESS_GIF_URL = "https://media1.tenor.com/m/gvjH24AtYM0AAAAC/minion-minions.gif"


# Este comando inicia a conversa e decide se o usuario ja pode ir direto ao chat.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = ensure_session(context)
    if session["rag_service"] is not None and session["collection"]:
        await reply(update, build_ready_message(session["files_count"], session["extraction_method"]))
        return

    if session["login_in_progress"] or session["loading_in_progress"]:
        await reply(
            update,
            "Já estou preparando o acesso aos seus documentos.\n"
            "Aguarde mais alguns instantes e eu aviso quando tudo estiver pronto.",
        )
        return

    await reply(
        update,
        f"Olá{display_name(update)}, tudo bem? 👋\n\n"
        "Estou aqui para te ajudar com os seus documentos ✨",
    )
    if session["extraction_method"]:
        await send_login_intro(update, context)
        return
    await send_extraction_choice_prompt(update, context)


# Este comando executa o login no Drive e prepara a base local para o chat.
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    session = ensure_session(context)
    if not session["extraction_method"]:
        await send_extraction_choice_prompt(update, context)
        return

    if session["login_in_progress"] or session["loading_in_progress"]:
        await reply(
            update,
            "A preparação já está em andamento.\n"
            "Conclua a autenticação no navegador, se ela ainda estiver aberta, e aguarde mais alguns instantes.",
        )
        return

    session["login_in_progress"] = True
    await reply(
        update,
        "🔓 Vou abrir o login do Google Drive no navegador desta máquina.\n\n"
        f"✅ Entre com sua conta e autorize o acesso para que eu importe os arquivos compatíveis da pasta '{DRIVE_FOLDER_NAME}'.",
    )

    try:
        drive_service, credentials = await asyncio.to_thread(login_google_drive)
    except Exception as exc:
        await reply(update, f"Não foi possível concluir a conexão com o Google Drive: {exc}")
        session["login_in_progress"] = False
        return

    session["login_in_progress"] = False
    session["loading_in_progress"] = True
    await reply(
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
        await reply(update, f"Não foi possível carregar os arquivos do Google Drive: {exc}")
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
            await reply_animation(update, SUCCESS_GIF_URL, success_caption)
        except Exception:
            await reply(update, success_caption)
    finally:
        session["login_in_progress"] = False
        session["loading_in_progress"] = False


# Este comando reapresenta o fluxo do Google Drive, sempre com Docling.
async def extractor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = ensure_session(context)
    if session["login_in_progress"] or session["loading_in_progress"]:
        await reply(
            update,
            "Ainda estou processando a importação atual.\n"
            "Aguarde terminar para reiniciar a conexão com o Google Drive.",
        )
        return

    reset_loaded_collection(session)
    session["extraction_method"] = None
    session["awaiting_extraction_choice"] = False
    await send_extraction_choice_prompt(update, context)


# Este comando limpa o historico textual da conversa atual.
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    session = ensure_session(context)
    session["messages"] = []
    await reply(
        update,
        "Pronto.\n"
        "Limpei o histórico da conversa. Pode enviar uma nova pergunta quando quiser.",
    )


# Este handler trata a mensagem livre do usuario e decide entre onboarding, rota direta e RAG.
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    session = ensure_session(context)
    if session["awaiting_extraction_choice"]:
        handled = await handle_extraction_choice(update, context, update.message.text)
        if handled:
            return

    if session["login_in_progress"]:
        await reply(
            update,
            "Ainda estou aguardando a conclusão do login no Google Drive.\n"
            "Termine a autenticação no navegador e tente novamente em seguida.",
        )
        return

    if session["loading_in_progress"]:
        await reply(
            update,
            "A conexão com o Google Drive já foi concluída.\n"
            "Agora ainda estou carregando os arquivos e preparando o chat.\n"
            "Aguarde mais alguns segundos.",
        )
        return

    if session["rag_service"] is None:
        if not session["extraction_method"]:
            handled = await handle_extraction_choice(update, context, update.message.text)
            if handled:
                return
            await send_extraction_choice_prompt(update, context)
            return

        await send_login_intro(update, context)
        return

    question = update.message.text.strip()
    recent_history = session["messages"][-6:]
    session["messages"].append({"role": "user", "content": question})

    direct_answer = build_collection_route_response(question, session)
    if direct_answer is not None:
        session["messages"].append({"role": "assistant", "content": direct_answer})
        await reply(update, direct_answer)
        return

    # So chegamos aqui quando a sessao ja tem um RAG pronto para responder perguntas.
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        answer = await asyncio.to_thread(session["rag_service"].ask_question, question, recent_history)
    except Exception as exc:
        answer = f"Erro ao obter resposta: {exc}"

    session["messages"].append({"role": "assistant", "content": answer})
    await reply(update, answer)
