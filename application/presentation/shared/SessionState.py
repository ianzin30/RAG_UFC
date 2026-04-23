"""Session-state bootstrap for the app shell."""

import streamlit as st


def initialize_app_session_state() -> None:
    defaults = {
        "messages": [],
        "collection": None,
        "current_collection": None,
        "rag_service": None,
        "drive_feedback": None,
        "upload_feedback": None,
        "upload_feedback_kind": "neutral",
        "upload_widget_version": 0,
        "chat_feedback": None,
        "last_upload_signature": None,
        "sidebar_panel": "chat",
        "app_theme": "dark",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
