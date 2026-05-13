"""Session-state helpers for active chat management."""

from __future__ import annotations

import streamlit as st

from presentation.shared.CollectionSelection import clone_collection_selection

from .Normalization import build_default_title, clone_messages
from .Normalization import build_timestamp_now
from .Storage import load_persisted_chat_state, persist_chat_state


def next_chat_id() -> str:
    next_id = st.session_state.get("next_chat_session_id", 1)
    st.session_state.next_chat_session_id = next_id + 1
    return f"chat_{next_id}"


def create_session(collection=None, model_name: str | None = None) -> dict[str, object]:
    timestamp = build_timestamp_now()
    return {
        "id": next_chat_id(),
        "title": build_default_title(),
        "collection": clone_collection_selection(collection),
        "model_name": model_name,
        "messages": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def get_chat_sessions() -> list[dict[str, object]]:
    return st.session_state.setdefault("chat_sessions", [])


def get_active_chat() -> dict[str, object] | None:
    active_chat_id = st.session_state.get("active_chat_id")
    for chat in get_chat_sessions():
        if chat["id"] == active_chat_id:
            return chat
    return get_chat_sessions()[0] if get_chat_sessions() else None


def save_active_chat(
    messages=None,
    collection=None,
    title: str | None = None,
    model_name: str | None = None,
    *,
    touch_recency: bool = True,
) -> None:
    active_chat = get_active_chat()
    if active_chat is None:
        return

    active_chat["messages"] = clone_messages(st.session_state.get("messages") if messages is None else messages)
    active_chat["collection"] = clone_collection_selection(
        st.session_state.get("collection") if collection is None else collection
    )
    active_chat["model_name"] = st.session_state.get("model_name") if model_name is None else model_name
    if title is not None:
        active_chat["title"] = title
    if touch_recency:
        active_chat["updated_at"] = build_timestamp_now()
    persist_chat_state(get_chat_sessions)


def sync_active_chat_to_state() -> None:
    active_chat = get_active_chat()
    if active_chat is None:
        st.session_state.messages = []
        st.session_state.collection = None
        st.session_state.current_collection = None
        st.session_state.rag_service = None
        return

    previous_collection = st.session_state.get("collection")
    previous_model = st.session_state.get("model_name")
    st.session_state.messages = clone_messages(active_chat.get("messages", []))
    st.session_state.collection = clone_collection_selection(active_chat.get("collection"))
    st.session_state.model_name = active_chat.get("model_name")
    if previous_collection != st.session_state.collection or previous_model != st.session_state.model_name:
        st.session_state.current_collection = None
        st.session_state.rag_service = None


def initialize_chat_sessions(
    user_id: str | None = None,
    default_collection=None,
    default_model: str | None = None,
) -> None:
    _ = user_id
    if "chat_sessions" not in st.session_state:
        persisted_state = load_persisted_chat_state()
        st.session_state.chat_sessions = persisted_state.get("chat_sessions", [])
        st.session_state.next_chat_session_id = persisted_state.get("next_chat_session_id", 1)
    elif "next_chat_session_id" not in st.session_state:
        st.session_state.next_chat_session_id = 1

    sessions = get_chat_sessions()
    if not sessions:
        sessions.append(create_session(collection=default_collection, model_name=default_model))

    active_chat_id = st.session_state.get("active_chat_id")
    if not active_chat_id or not any(chat["id"] == active_chat_id for chat in sessions):
        st.session_state.active_chat_id = sessions[0]["id"]

    active_chat = get_active_chat()
    if active_chat and active_chat.get("collection") is None and default_collection is not None:
        active_chat["collection"] = default_collection
    if active_chat and active_chat.get("model_name") is None and default_model is not None:
        active_chat["model_name"] = default_model

    sync_active_chat_to_state()
    persist_chat_state(get_chat_sessions)
