"""Persistence helpers for chat sessions — MongoDB-backed, per-user isolated."""

import logging

import streamlit as st

logger = logging.getLogger("ragufc.storage")


def _get_mongo_db():
    from service.storage.MongoClientProvider import get_db
    return get_db()


def load_persisted_chat_state(user_id: str | None = None) -> dict[str, object]:
    """Load chat sessions for *user_id* from MongoDB.

    Falls back to empty state on any error (MongoDB unavailable, first run, etc.).
    When user_id is None (Firebase disabled / dev mode), returns empty state.
    """
    if not user_id:
        return {}

    try:
        from service.storage.UserChatRepository import load_chat_state
        state = load_chat_state(_get_mongo_db(), user_id)
        logger.info(
            "Chat state loaded — uid=%s sessions=%d",
            user_id,
            len(state.get("chat_sessions", [])),
        )
        return state
    except Exception as exc:
        logger.warning("Failed to load chat state from MongoDB (uid=%s): %s", user_id, exc)
        return {}


def persist_chat_state(get_chat_sessions, user_id: str | None = None) -> None:
    """Save the current sessions list for *user_id* to MongoDB.

    When user_id is None (Firebase disabled / dev mode), does nothing.
    """
    if not user_id:
        return

    sessions = get_chat_sessions()
    active_chat_id = st.session_state.get("active_chat_id")
    next_id = st.session_state.get("next_chat_session_id", 1)

    try:
        from service.storage.UserChatRepository import save_chat_state
        save_chat_state(
            _get_mongo_db(),
            user_id,
            sessions,
            active_chat_id,
            next_id,
        )
    except Exception as exc:
        logger.warning("Failed to persist chat state to MongoDB (uid=%s): %s", user_id, exc)
