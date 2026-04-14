"""Selection-state helpers for collection switching."""

import streamlit as st

from presentation import chat_sessions
from presentation.collection_selection import (
    add_collection_selection,
    normalize_collection_selection,
    toggle_collection_selection,
)


def set_selected_collections(collections) -> None:
    normalized = normalize_collection_selection(collections)
    current = normalize_collection_selection(st.session_state.get("collection"))
    if current == normalized:
        return

    st.session_state.current_collection = None
    st.session_state.rag_service = None
    chat_sessions.update_active_chat_collection(normalized or None)


def toggle_collection(collection_name: str | None) -> None:
    set_selected_collections(toggle_collection_selection(st.session_state.get("collection"), collection_name))


def add_collection(collection_name: str | None) -> None:
    set_selected_collections(add_collection_selection(st.session_state.get("collection"), collection_name))
