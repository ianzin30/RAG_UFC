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
        # Google Drive OAuth state machine
        "gdrive_status": "idle",  # idle | importing | connected | error
        "gdrive_oauth_state": None,  # opaque state token sent to Google
        "gdrive_code_verifier": None,  # PKCE verifier used when Google redirects back
        "gdrive_auth_url": None,  # authorize URL pending user click
        "gdrive_credentials_json": None,  # serialized credentials cached in session
        "gdrive_error": None,  # last Drive error message
        "gdrive_import_result": None,  # latest import summary (file count + collection name)
        "gdrive_import_progress": None,  # live import counter shown while Drive files process
        "gdrive_import_job_id": None,  # active background Drive import job id
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
