import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATION_ROOT = PROJECT_ROOT / "application"
for path in (PROJECT_ROOT, APPLICATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from presentation.app_shell.chat_history import build_chat_history_sections
from presentation.chat_sessions_support.normalization import coerce_chat_session


def test_coerce_chat_session_adds_compatible_timestamps():
    normalized = coerce_chat_session(
        {
            "id": "chat_1",
            "title": "Primeiro chat",
            "collection": ["google_drive_rag"],
            "messages": [{"role": "user", "content": "oi"}],
        }
    )

    assert normalized is not None
    assert isinstance(normalized.get("created_at"), str)
    assert isinstance(normalized.get("updated_at"), str)
    assert normalized["created_at"]
    assert normalized["updated_at"]


def test_build_chat_history_sections_groups_today_yesterday_and_older():
    now = datetime(2026, 4, 13, 15, 0, tzinfo=timezone.utc)
    today_iso = now.isoformat()
    yesterday_iso = (now - timedelta(days=1)).isoformat()
    older_iso = (now - timedelta(days=5)).isoformat()

    sections = build_chat_history_sections(
        [
            {"id": "chat_1", "title": "Hoje", "updated_at": today_iso},
            {"id": "chat_2", "title": "Ontem", "updated_at": yesterday_iso},
            {"id": "chat_3", "title": "Antigo", "updated_at": older_iso},
        ],
        now=now,
    )

    assert [section["label"] for section in sections] == ["Today", "Yesterday", "Older"]
    assert sections[0]["items"][0]["id"] == "chat_1"
    assert sections[1]["items"][0]["id"] == "chat_2"
    assert sections[2]["items"][0]["id"] == "chat_3"


def test_build_chat_history_sections_sorts_recent_items_first_inside_section():
    now = datetime(2026, 4, 13, 15, 0, tzinfo=timezone.utc)
    sections = build_chat_history_sections(
        [
            {"id": "chat_older", "title": "Mais cedo", "updated_at": (now - timedelta(hours=6)).isoformat()},
            {"id": "chat_newer", "title": "Agora", "updated_at": now.isoformat()},
        ],
        now=now,
    )

    assert [item["id"] for item in sections[0]["items"]] == ["chat_newer", "chat_older"]
