"""
Sidebar layout and composition - renders the left navigation panel.

The sidebar contains:
- Vertical navigation rail (narrow left column) for account menu and panel switching
- Main content panel (wider right area) for chat or files view
- Feedback messages for uploads and chat operations
"""

import streamlit as st

from .ChatPanel import render_chat_panel
from .FilesPanel import render_files_panel
from presentation.nav_rail.Navigation import render_navigation_rail
from .Uploads import render_notice


def render_sidebar(
    available_documents: list[dict[str, str]],
    default_collection,
    default_model: str | None,
) -> None:
    """Render the main sidebar with navigation rail and content panels."""
    with st.sidebar:
        # Retrieve any pending feedback messages
        upload_feedback = st.session_state.pop("upload_feedback", None)
        chat_feedback = st.session_state.pop("chat_feedback", None)
        upload_feedback_kind = st.session_state.pop("upload_feedback_kind", "neutral")

        with st.container(key="sidebar_layout_shell"):
            st.markdown(
                """
                <span id="sidebar-chat-panel" class="sidebar-panel-target"></span>
                <span id="sidebar-files-panel" class="sidebar-panel-target"></span>
                """,
                unsafe_allow_html=True,
            )
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

                    with st.container(key="sidebar_chat_panel_view"):
                        render_chat_panel(default_collection, default_model)
                    with st.container(key="sidebar_files_panel_view"):
                        render_files_panel(available_documents)
