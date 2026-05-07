"""
Sidebar layout and composition - renders the left navigation panel.

The sidebar contains:
- Vertical navigation rail (narrow left column) for theme, etc.
- Main content panel (wider right area) for chat or files view
- Feedback messages for uploads and chat operations
- Sign-out button when the user is authenticated
"""

import streamlit as st

from .ChatPanel import render_chat_panel
from .FilesPanel import render_files_panel
from presentation.nav_rail.Navigation import SIDEBAR_CHAT_PANEL, get_active_sidebar_panel, render_navigation_rail
from .Uploads import render_notice


def render_sidebar(
    available_documents: list[dict[str, str]],
    default_collection,
    default_model: str | None,
    user=None,
) -> None:
    """Render the main sidebar with navigation rail and content panels."""
    with st.sidebar:
        # Sign-out button when authenticated
        if user is not None:
            from service.RuntimeConfig import get_runtime_config
            try:
                firebase_enabled = get_runtime_config().firebase.enabled
            except Exception:
                firebase_enabled = False

            if firebase_enabled:
                with st.container(key="sidebar_user_shell"):
                    display = user.display_name or user.email or "Usuário"
                    st.caption(f"👤 {display}")
                    if st.button("Sair", key="sidebar_logout_btn", use_container_width=True):
                        from presentation.auth.LoginGate import logout
                        logout()

        # Retrieve any pending feedback messages
        upload_feedback = st.session_state.pop("upload_feedback", None)
        chat_feedback = st.session_state.pop("chat_feedback", None)
        upload_feedback_kind = st.session_state.pop("upload_feedback_kind", "neutral")

        with st.container(key="sidebar_layout_shell"):
            # Two-column layout: narrow rail + wide content panel
            rail_col, panel_col = st.columns([18, 82], gap=None)

            with rail_col:
                # Navigation rail (narrow vertical menu)
                render_navigation_rail()

            with panel_col:
                with st.container(key="sidebar_panel_shell"):
                    if upload_feedback:
                        render_notice(upload_feedback, kind=upload_feedback_kind)
                    if chat_feedback:
                        render_notice(chat_feedback)

                    active_panel = get_active_sidebar_panel()
                    if active_panel == SIDEBAR_CHAT_PANEL:
                        render_chat_panel(default_collection, default_model)
                    else:
                        render_files_panel(available_documents)
