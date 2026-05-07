"""Tests for UserChatRepository — isolation guarantees and CRUD."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_db():
    """Return a minimal in-memory MongoDB substitute using MagicMock with simple dicts."""
    # Use mongomock if available, otherwise skip
    try:
        import mongomock
        client = mongomock.MongoClient()
        return client["test_rag_ufc"]
    except ImportError:
        pytest.skip("mongomock not installed — skipping MongoDB tests")


def _make_session(chat_id: str, title: str, messages=None) -> dict:
    return {
        "id": chat_id,
        "title": title,
        "collection": None,
        "model_name": "phi4:latest",
        "messages": messages or [],
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


def test_user_a_cannot_read_user_b_sessions(mock_db):
    from service.storage.UserChatRepository import save_chat_state, load_chat_state

    session_a = _make_session("chat_1", "Chat A", messages=[{"role": "user", "content": "Hello"}])
    save_chat_state(mock_db, "user_a", [session_a], "chat_1", 2)

    state_b = load_chat_state(mock_db, "user_b")
    assert state_b["chat_sessions"] == []


def test_save_and_load_roundtrip(mock_db):
    from service.storage.UserChatRepository import save_chat_state, load_chat_state

    session = _make_session("chat_1", "My Chat", messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ])
    save_chat_state(mock_db, "user_x", [session], "chat_1", 2)

    state = load_chat_state(mock_db, "user_x")
    assert len(state["chat_sessions"]) == 1
    loaded = state["chat_sessions"][0]
    assert loaded["title"] == "My Chat"
    assert len(loaded["messages"]) == 2
    assert loaded["messages"][0]["content"] == "Hello"


def test_deleted_sessions_removed_from_mongo(mock_db):
    from service.storage.UserChatRepository import save_chat_state, load_chat_state

    s1 = _make_session("chat_1", "First")
    s2 = _make_session("chat_2", "Second")
    save_chat_state(mock_db, "user_x", [s1, s2], "chat_1", 3)

    # Delete s2 by not including it in the next save
    save_chat_state(mock_db, "user_x", [s1], "chat_1", 3)

    state = load_chat_state(mock_db, "user_x")
    ids = [s["id"] for s in state["chat_sessions"]]
    assert "chat_2" not in ids
    assert "chat_1" in ids


def test_user_b_save_does_not_overwrite_user_a(mock_db):
    from service.storage.UserChatRepository import save_chat_state, load_chat_state

    session_a = _make_session("chat_1", "A's chat")
    save_chat_state(mock_db, "user_a", [session_a], "chat_1", 2)

    session_b = _make_session("chat_1", "B's chat")
    save_chat_state(mock_db, "user_b", [session_b], "chat_1", 2)

    state_a = load_chat_state(mock_db, "user_a")
    assert state_a["chat_sessions"][0]["title"] == "A's chat"
