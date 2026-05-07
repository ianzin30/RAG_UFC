"""Smoke tests for the LoginGate auth flow logic."""
import pytest
from unittest.mock import patch, MagicMock


def _make_session_state(initial=None):
    """Return a simple dict that mimics st.session_state for testing."""
    state = {}
    if initial:
        state.update(initial)
    return state


def test_require_authenticated_user_returns_none_when_firebase_disabled():
    """When Firebase is disabled, require_authenticated_user returns None without stopping."""
    with patch("presentation.auth.LoginGate.is_firebase_enabled", return_value=False):
        from presentation.auth.LoginGate import require_authenticated_user
        result = require_authenticated_user()
    assert result is None


def test_require_authenticated_user_returns_existing_user():
    """When a UserContext is already in session_state, it is returned immediately."""
    from service.auth.UserContext import UserContext
    mock_user = UserContext(user_id="uid123", email="a@b.com")

    with patch("presentation.auth.LoginGate.is_firebase_enabled", return_value=True), \
         patch("presentation.auth.LoginGate.get_current_user", return_value=mock_user):
        from presentation.auth import LoginGate
        # Reload to pick up patches
        import importlib
        importlib.reload(LoginGate)

        result = LoginGate.require_authenticated_user()

    assert result is not None
    assert result.user_id == "uid123"


def test_clear_current_user_clears_session_keys():
    """clear_current_user removes the expected keys from session_state."""
    import streamlit as st
    from unittest.mock import patch, MagicMock

    mock_state = {
        "user": MagicMock(),
        "firebase_id_token": "token",
        "chat_sessions": [{"id": "chat_1"}],
        "messages": ["msg"],
        "rag_service": MagicMock(),
    }

    with patch.object(type(st.session_state), "__getitem__", lambda s, k: mock_state.get(k)), \
         patch.object(type(st.session_state), "__setitem__", lambda s, k, v: mock_state.__setitem__(k, v)), \
         patch.object(type(st.session_state), "pop", lambda s, k, d=None: mock_state.pop(k, d)):
        from presentation.auth.SessionUser import clear_current_user
        clear_current_user()

    assert mock_state.get("user") is None
    assert mock_state.get("firebase_id_token") is None
