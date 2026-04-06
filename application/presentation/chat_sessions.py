import json
import re
from copy import deepcopy
from pathlib import Path

import streamlit as st

from presentation.collection_selection import clone_collection_selection

DEFAULT_CHAT_TITLE = "Nova conversa"
MAX_CHAT_SESSIONS = 3
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHAT_STORAGE_PATH = PROJECT_ROOT / "data" / "local_chat_sessions.json"


def _coerce_messages(messages) -> list[dict[str, str]]:
    normalized_messages: list[dict[str, str]] = []
    for message in list(messages or []):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", ""))
        if not role:
            continue
        normalized_messages.append({"role": role, "content": content})
    return normalized_messages


def _coerce_chat_session(chat) -> dict[str, object] | None:
    if not isinstance(chat, dict):
        return None

    chat_id = str(chat.get("id", "")).strip()
    title = str(chat.get("title", "")).strip()
    if not chat_id or not title:
        return None

    return {
        "id": chat_id,
        "title": title,
        "collection": clone_collection_selection(chat.get("collection")),
        "model_name": str(chat.get("model_name", "")).strip() or None,
        "messages": _coerce_messages(chat.get("messages")),
    }


def _infer_next_chat_id(sessions: list[dict[str, object]]) -> int:
    highest = 0
    for chat in sessions:
        match = re.fullmatch(r"chat_(\d+)", str(chat.get("id", "")).strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def _load_persisted_chat_state() -> dict[str, object]:
    if not CHAT_STORAGE_PATH.exists():
        return {}

    try:
        payload = json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_sessions = payload.get("chat_sessions", [])
    sessions = []
    for raw_chat in raw_sessions:
        normalized = _coerce_chat_session(raw_chat)
        if normalized is not None:
            sessions.append(normalized)

    active_chat_id = str(payload.get("active_chat_id", "")).strip() or None
    if active_chat_id and not any(chat["id"] == active_chat_id for chat in sessions):
        active_chat_id = sessions[0]["id"] if sessions else None

    next_chat_session_id = payload.get("next_chat_session_id")
    if not isinstance(next_chat_session_id, int) or next_chat_session_id < 1:
        next_chat_session_id = _infer_next_chat_id(sessions)

    return {
        "chat_sessions": sessions,
        "active_chat_id": active_chat_id,
        "next_chat_session_id": next_chat_session_id,
    }


def _persist_chat_state() -> None:
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chat_sessions": get_chat_sessions(),
        "active_chat_id": st.session_state.get("active_chat_id"),
        "next_chat_session_id": st.session_state.get("next_chat_session_id", 1),
    }
    temp_path = CHAT_STORAGE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(CHAT_STORAGE_PATH)


def _next_chat_id() -> str:
    next_id = st.session_state.get("next_chat_session_id", 1)
    st.session_state.next_chat_session_id = next_id + 1
    return f"chat_{next_id}"


def _build_default_title() -> str:
    titles = {chat["title"] for chat in st.session_state.get("chat_sessions", [])}
    if DEFAULT_CHAT_TITLE not in titles:
        return DEFAULT_CHAT_TITLE

    index = 2
    while f"{DEFAULT_CHAT_TITLE} {index}" in titles:
        index += 1
    return f"{DEFAULT_CHAT_TITLE} {index}"


def _clone_messages(messages) -> list[dict[str, str]]:
    return deepcopy(list(messages or []))


def _truncate_title(text: str, max_length: int = 34) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return _build_default_title()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def create_session(collection=None, model_name: str | None = None) -> dict[str, object]:
    return {
        "id": _next_chat_id(),
        "title": _build_default_title(),
        "collection": clone_collection_selection(collection),
        "model_name": model_name,
        "messages": [],
    }


def get_chat_sessions() -> list[dict[str, object]]:
    return st.session_state.setdefault("chat_sessions", [])


def get_active_chat() -> dict[str, object] | None:
    active_chat_id = st.session_state.get("active_chat_id")
    for chat in get_chat_sessions():
        if chat["id"] == active_chat_id:
            return chat
    return get_chat_sessions()[0] if get_chat_sessions() else None


def save_active_chat(messages=None, collection=None, title: str | None = None, model_name: str | None = None) -> None:
    active_chat = get_active_chat()
    if active_chat is None:
        return

    active_chat["messages"] = _clone_messages(st.session_state.get("messages") if messages is None else messages)
    active_chat["collection"] = clone_collection_selection(
        st.session_state.get("collection") if collection is None else collection
    )
    active_chat["model_name"] = st.session_state.get("model_name") if model_name is None else model_name
    if title is not None:
        active_chat["title"] = title
    _persist_chat_state()


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
    st.session_state.messages = _clone_messages(active_chat.get("messages", []))
    st.session_state.collection = clone_collection_selection(active_chat.get("collection"))
    st.session_state.model_name = active_chat.get("model_name")
    if previous_collection != st.session_state.collection or previous_model != st.session_state.model_name:
        st.session_state.current_collection = None
        st.session_state.rag_service = None


def initialize_chat_sessions(default_collection=None, default_model: str | None = None) -> None:
    if "chat_sessions" not in st.session_state:
        persisted_state = _load_persisted_chat_state()
        st.session_state.chat_sessions = persisted_state.get("chat_sessions", [])
        if persisted_state.get("active_chat_id"):
            st.session_state.active_chat_id = persisted_state["active_chat_id"]
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
    _persist_chat_state()


def create_new_chat(default_collection=None, default_model: str | None = None) -> tuple[bool, str | None]:
    sessions = get_chat_sessions()
    if len(sessions) >= MAX_CHAT_SESSIONS:
        return False, f"Voce pode manter ate {MAX_CHAT_SESSIONS} chats ao mesmo tempo."

    save_active_chat()
    new_chat = create_session(collection=default_collection, model_name=default_model)
    sessions.insert(0, new_chat)
    st.session_state.active_chat_id = new_chat["id"]
    sync_active_chat_to_state()
    return True, None


def rename_chat(chat_id: str, new_title: str) -> tuple[bool, str | None]:
    normalized = re.sub(r"\s+", " ", (new_title or "").strip())
    if not normalized:
        return False, "Digite um nome para o chat."

    for chat in get_chat_sessions():
        if chat["id"] == chat_id:
            chat["title"] = _truncate_title(normalized)
            _persist_chat_state()
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
    _persist_chat_state()
    return True, None


def activate_chat(chat_id: str) -> None:
    if st.session_state.get("active_chat_id") == chat_id:
        return

    save_active_chat()
    st.session_state.active_chat_id = chat_id
    sync_active_chat_to_state()
    _persist_chat_state()


def update_active_chat_collection(collection) -> None:
    st.session_state.collection = clone_collection_selection(collection)
    save_active_chat(collection=collection)


def update_active_chat_model(model_name: str) -> None:
    st.session_state.model_name = model_name
    save_active_chat(model_name=model_name)


def update_active_chat_messages(messages) -> None:
    st.session_state.messages = _clone_messages(messages)
    save_active_chat(messages=messages)


def maybe_title_active_chat(prompt: str) -> None:
    active_chat = get_active_chat()
    if active_chat is None:
        return

    title = str(active_chat.get("title", "")).strip()
    if title.startswith(DEFAULT_CHAT_TITLE):
        active_chat["title"] = _truncate_title(prompt)
        _persist_chat_state()
