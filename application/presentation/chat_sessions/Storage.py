"""Shared local persistence helpers for chat sessions."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import streamlit as st

from .Constants import CHAT_STORAGE_PATH

logger = logging.getLogger("ragufc.storage")

_CHAT_STORAGE_LOCK = threading.Lock()


def _empty_state() -> dict[str, object]:
    return {
        "chat_sessions": [],
        "next_chat_session_id": 1,
    }


def _coerce_state(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return _empty_state()

    sessions = payload.get("chat_sessions")
    if not isinstance(sessions, list):
        sessions = []

    try:
        next_id = int(payload.get("next_chat_session_id") or 1)
    except (TypeError, ValueError):
        next_id = 1

    return {
        "chat_sessions": sessions,
        "next_chat_session_id": max(1, next_id),
    }


def load_persisted_chat_state(user_id: str | None = None) -> dict[str, object]:
    """Load the shared chat sessions from data/local_chat_sessions.json.

    The *user_id* parameter is accepted for old call sites but ignored. Active
    chat selection stays browser-session-local and is intentionally not loaded.
    """
    _ = user_id
    path = Path(CHAT_STORAGE_PATH)
    if not path.exists():
        return _empty_state()

    try:
        with _CHAT_STORAGE_LOCK:
            payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load shared chat state from %s: %s", path, exc)
        return _empty_state()

    state = _coerce_state(payload)
    logger.info("Shared chat state loaded - sessions=%d", len(state["chat_sessions"]))
    return state


def persist_chat_state(get_chat_sessions, user_id: str | None = None) -> None:
    """Persist shared chat sessions to data/local_chat_sessions.json atomically."""
    _ = user_id
    path = Path(CHAT_STORAGE_PATH)
    payload = {
        "chat_sessions": get_chat_sessions(),
        "next_chat_session_id": int(st.session_state.get("next_chat_session_id", 1) or 1),
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp")
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        with _CHAT_STORAGE_LOCK:
            tmp_path.write_text(serialized, encoding="utf-8")
            tmp_path.replace(path)
    except Exception as exc:
        logger.warning("Failed to persist shared chat state to %s: %s", path, exc)
