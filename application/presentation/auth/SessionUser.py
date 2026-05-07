"""Helpers for reading/writing the authenticated UserContext in st.session_state."""
from __future__ import annotations

import streamlit as st

from service.auth.UserContext import UserContext


def get_current_user() -> UserContext | None:
    return st.session_state.get("user")


def set_current_user(user: UserContext) -> None:
    st.session_state["user"] = user


def clear_current_user() -> None:
    st.session_state["user"] = None
    st.session_state["firebase_id_token"] = None
    # Clear chat/upload caches so the next login starts fresh
    for key in ("chat_sessions", "active_chat_id", "next_chat_session_id",
                "messages", "collection", "current_collection", "rag_service",
                "last_upload_signature"):
        st.session_state.pop(key, None)
