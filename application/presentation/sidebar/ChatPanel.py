"""Sidebar rendering for chat session controls."""

import streamlit as st

from .ChatHistory import render_chat_history


def render_chat_panel(default_collection, default_model: str | None) -> None:
    with st.container(key="sidebar_chat_shell"):
        render_chat_history(default_collection, default_model)
