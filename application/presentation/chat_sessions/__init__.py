"""
Chat session management - handles creating, loading, and maintaining chat conversations.

This module provides functions to:
- Create and activate chat sessions
- Store and retrieve conversation history
- Manage session metadata (title, model, collections)
- Persist sessions to storage for recovery across app restarts
"""

from .Operations import (
    activate_chat,
    create_new_chat,
    delete_chat,
    maybe_title_active_chat,
    rename_chat,
    update_active_chat_collection,
    update_active_chat_messages,
    update_active_chat_model,
)
from .State import (
    create_session,
    get_active_chat,
    get_chat_sessions,
    initialize_chat_sessions,
    save_active_chat,
    sync_active_chat_to_state,
)

__all__ = [
    "activate_chat",
    "create_new_chat",
    "create_session",
    "delete_chat",
    "get_active_chat",
    "get_chat_sessions",
    "initialize_chat_sessions",
    "maybe_title_active_chat",
    "rename_chat",
    "save_active_chat",
    "sync_active_chat_to_state",
    "update_active_chat_collection",
    "update_active_chat_messages",
    "update_active_chat_model",
]
