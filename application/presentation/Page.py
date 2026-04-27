"""
Main page layout and composition for the RAG Chat application.

This module orchestrates the overall page structure: initializes session state,
configures the page, loads available collections and documents, and renders
the sidebar and main chat area. It serves as the entry point for the presentation layer.
"""

import streamlit as st

from presentation import chat_sessions
from presentation.chat import Chat as chat
from presentation.shared.CollectionSelection import normalize_collection_selection, sanitize_collection_selection
from service.RuntimeConfig import get_runtime_config

from .sidebar.Collections import list_available_collections, list_collection_documents
from .shared.Config import LOGO_PATH
from .sidebar.Selection import set_selected_collections
from .shared.SessionState import initialize_app_session_state
from .sidebar.Sidebar import render_sidebar
from .shared.Styles import apply_global_styles
from .shared.Theme import get_active_theme_name


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
    default_model = get_runtime_config().ufc_model_name
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
