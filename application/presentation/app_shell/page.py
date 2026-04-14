"""Top-level page composition for the Streamlit app."""

import os

import streamlit as st

from presentation import chat, chat_sessions
from presentation.collection_selection import normalize_collection_selection, sanitize_collection_selection

from .collections import list_available_collections, list_collection_documents
from .config import LOGO_PATH
from .selection import set_selected_collections
from .session_state import initialize_app_session_state
from .sidebar import render_sidebar
from .styles import apply_global_styles
from .theme import get_active_theme_name


def render_application() -> None:
    initialize_app_session_state()
    st.set_page_config(
        page_title="RAG Treino",
        page_icon=str(LOGO_PATH),
        layout="wide",
    )
    apply_global_styles(get_active_theme_name())

    available_documents = list_collection_documents()
    available_collections = list_available_collections(available_documents)
    default_collection = [available_collections[0]] if available_collections else None
    default_model = os.getenv("UFC_MODEL_NAME")
    chat_sessions.initialize_chat_sessions(default_collection=default_collection, default_model=default_model)

    selected_collections = sanitize_collection_selection(st.session_state.get("collection"), available_collections)
    if normalize_collection_selection(st.session_state.get("collection")) != selected_collections:
        set_selected_collections(selected_collections)
    elif not selected_collections and default_collection:
        set_selected_collections(default_collection)

    render_sidebar(available_documents, default_collection, default_model)
    with st.container(key="main_view_shell"):
        with st.container(key="main_view_toolbar_shell"):
            selected_model = chat.render_model_toolbar()
        with st.container(key="main_view_body_shell"):
            chat.show(selected_model)
