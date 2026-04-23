"""Persistence helpers for chat sessions."""

import json

import streamlit as st

from .Constants import CHAT_STORAGE_PATH
from .Normalization import coerce_chat_session, infer_next_chat_id


def load_persisted_chat_state() -> dict[str, object]:
    if not CHAT_STORAGE_PATH.exists():
        return {}

    try:
        payload = json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    raw_sessions = payload.get("chat_sessions", [])
    sessions = []
    for raw_chat in raw_sessions:
        normalized = coerce_chat_session(raw_chat)
        if normalized is not None:
            sessions.append(normalized)

    active_chat_id = str(payload.get("active_chat_id", "")).strip() or None
    if active_chat_id and not any(chat["id"] == active_chat_id for chat in sessions):
        active_chat_id = sessions[0]["id"] if sessions else None

    next_chat_session_id = payload.get("next_chat_session_id")
    if not isinstance(next_chat_session_id, int) or next_chat_session_id < 1:
        next_chat_session_id = infer_next_chat_id(sessions)

    return {
        "chat_sessions": sessions,
        "active_chat_id": active_chat_id,
        "next_chat_session_id": next_chat_session_id,
    }


def persist_chat_state(get_chat_sessions) -> None:
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chat_sessions": get_chat_sessions(),
        "active_chat_id": st.session_state.get("active_chat_id"),
        "next_chat_session_id": st.session_state.get("next_chat_session_id", 1),
    }
    temp_path = CHAT_STORAGE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(CHAT_STORAGE_PATH)
