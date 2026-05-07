"""
Session state initialization.

Initializes Streamlit session variables that persist across app reruns.
This includes chat messages, selected collections, the RAG service instance,
and UI state like theme and active sidebar panel.
"""

import streamlit as st


def initialize_app_session_state() -> None:
    """Initialize session state variables with their default values."""
    defaults = {
        "messages": [],  # Chat conversation history
        "collection": None,  # Currently selected document collection(s)
        "current_collection": None,  # Cached current collection
        "rag_service": None,  # RAG service instance (loaded on demand)
        "drive_feedback": None,  # Feedback message from Google Drive integration
        "upload_feedback": None,  # Feedback message from file uploads
        "upload_feedback_kind": "neutral",  # Feedback message style (success/error/neutral)
        "upload_widget_version": 0,  # Version tracker to reset upload widget
        "chat_feedback": None,  # Feedback message from chat operations
        "last_upload_signature": None,  # Signature of last uploaded files (to detect new uploads)
        "sidebar_panel": "chat",  # Active sidebar panel (chat or files)
        "app_theme": "dark",  # Current theme (dark or light)
        "user": None,  # Authenticated UserContext (set by LoginGate)
        "firebase_id_token": None,  # Raw Firebase ID token (for re-verification if needed)
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
