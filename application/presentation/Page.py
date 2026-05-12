"""
Main page layout and composition for the RAG Chat application.

This module orchestrates the overall page structure: initializes session state,
configures the page, loads available collections and documents, and renders
the sidebar and main chat area. It serves as the entry point for the presentation layer.
"""

import streamlit as st
import logging

from presentation import chat_sessions
from presentation.chat import Chat as chat
from presentation.integrations.GoogleDrive import run_pending_google_drive_import
from presentation.shared.CollectionSelection import normalize_collection_selection, sanitize_collection_selection
from service.RuntimeConfig import get_runtime_config

from .sidebar.Collections import list_available_collections, list_collection_documents
from .sidebar.Selection import set_selected_collections
from .shared.SessionState import initialize_app_session_state
from .sidebar.Sidebar import render_sidebar


logger = logging.getLogger(__name__)


def render_application() -> None:
    initialize_app_session_state()

    available_documents = list_collection_documents()
    available_collections = list_available_collections(available_documents)
    default_collection = [available_collections[0]] if available_collections else None
    default_model = get_runtime_config().ufc_model_name
    if not st.session_state.get("_default_model_logged"):
        logger.info("Default UI LLM model loaded from config: %s", default_model)
        st.session_state._default_model_logged = True
    chat_sessions.initialize_chat_sessions(
        default_collection=default_collection, default_model=default_model
    )

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
            if run_pending_google_drive_import():
                return
            chat.show(selected_model)
