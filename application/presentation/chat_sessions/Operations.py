"""Operations for chat creation, activation, and updates."""

from __future__ import annotations

import re

import streamlit as st

from .Constants import DEFAULT_CHAT_TITLE, MAX_CHAT_SESSIONS
from .Normalization import build_timestamp_now, clone_messages, truncate_title
from .State import (
    create_session,
    get_active_chat,
    get_chat_sessions,
    save_active_chat,
    sync_active_chat_to_state,
)
from .Storage import persist_chat_state


def create_new_chat(default_collection=None, default_model: str | None = None) -> tuple[bool, str | None]:
    sessions = get_chat_sessions()
    if len(sessions) >= MAX_CHAT_SESSIONS:
        return False, f"Voce pode manter ate {MAX_CHAT_SESSIONS} chats ao mesmo tempo."

    save_active_chat()
    new_chat = create_session(collection=default_collection, model_name=default_model)
    sessions.insert(0, new_chat)
    st.session_state.active_chat_id = new_chat["id"]
    sync_active_chat_to_state()
    persist_chat_state(get_chat_sessions)
    return True, None


def rename_chat(chat_id: str, new_title: str) -> tuple[bool, str | None]:
    normalized = re.sub(r"\s+", " ", (new_title or "").strip())
    if not normalized:
        return False, "Digite um nome para o chat."

    for chat in get_chat_sessions():
        if chat["id"] == chat_id:
            chat["title"] = truncate_title(normalized)
            chat["updated_at"] = build_timestamp_now()
            persist_chat_state(get_chat_sessions)
            return True, None
    return False, "Chat nao encontrado."


def delete_chat(chat_id: str, default_collection=None, default_model: str | None = None) -> tuple[bool, str | None]:
    sessions = get_chat_sessions()
    if not sessions:
        return False, "Nenhum chat para excluir."

    delete_index = next((index for index, chat in enumerate(sessions) if chat["id"] == chat_id), None)
    if delete_index is None:
        return False, "Chat nao encontrado."

    del sessions[delete_index]
    if not sessions:
        sessions.append(create_session(collection=default_collection, model_name=default_model))

    if st.session_state.get("active_chat_id") == chat_id:
        st.session_state.active_chat_id = sessions[0]["id"]

    sync_active_chat_to_state()
    persist_chat_state(get_chat_sessions)
    return True, None


def activate_chat(chat_id: str) -> None:
    sessions = get_chat_sessions()
    target_index = next((index for index, chat in enumerate(sessions) if chat["id"] == chat_id), None)
    if target_index is None:
        return

    if st.session_state.get("active_chat_id") != chat_id:
        save_active_chat(touch_recency=False)

    st.session_state.active_chat_id = chat_id
    sessions[target_index]["updated_at"] = build_timestamp_now()
    sessions.insert(0, sessions.pop(target_index))
    sync_active_chat_to_state()
    persist_chat_state(get_chat_sessions)


def update_active_chat_collection(collection) -> None:
    st.session_state.collection = collection
    save_active_chat(collection=collection)


def update_active_chat_model(model_name: str) -> None:
    st.session_state.model_name = model_name
    save_active_chat(model_name=model_name)


def update_active_chat_messages(messages) -> None:
    st.session_state.messages = clone_messages(messages)
    save_active_chat(messages=messages)


def maybe_title_active_chat(prompt: str) -> None:
    active_chat = get_active_chat()
    if active_chat is None:
        return

    title = str(active_chat.get("title", "")).strip()
    if title.startswith(DEFAULT_CHAT_TITLE):
        active_chat["title"] = truncate_title(prompt)
        active_chat["updated_at"] = build_timestamp_now()
        persist_chat_state(get_chat_sessions)
