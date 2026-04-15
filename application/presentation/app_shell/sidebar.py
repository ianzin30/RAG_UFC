"""Sidebar composition for the Streamlit app shell."""

import streamlit as st

from .chat_panel import render_chat_panel
from .files_panel import render_files_panel
from .navigation import SIDEBAR_CHAT_PANEL, get_active_sidebar_panel, render_navigation_rail
from .uploads import render_notice


def render_sidebar(available_documents: list[dict[str, str]], default_collection, default_model: str | None) -> None:
    with st.sidebar:
        upload_feedback = st.session_state.pop("upload_feedback", None)
        chat_feedback = st.session_state.pop("chat_feedback", None)
        upload_feedback_kind = st.session_state.pop("upload_feedback_kind", "neutral")
        with st.container(key="sidebar_layout_shell"):
            rail_col, panel_col = st.columns([18, 82], gap=None)

            with rail_col:
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
