"""chat_sessions and chat_messages collections — all queries filter by user_id."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from pymongo.database import Database

logger = logging.getLogger("ragufc.storage")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_next_chat_id(sessions: list[dict]) -> int:
    highest = 0
    for chat in sessions:
        m = re.fullmatch(r"chat_(\d+)", str(chat.get("id", "")).strip())
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def _doc_to_session(doc: dict) -> dict:
    """Convert a Mongo document to the in-memory chat session dict."""
    doc.pop("_id", None)
    doc.pop("user_id", None)
    return doc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_chat_state(db: Database, user_id: str) -> dict:
    """Load all chat sessions for *user_id* from MongoDB.

    Returns the same shape expected by presentation/chat_sessions/Storage.py:
    {chat_sessions, active_chat_id, next_chat_session_id}
    """
    raw_sessions = list(
        db["chat_sessions"]
        .find({"user_id": user_id}, {"_id": 0, "user_id": 0})
        .sort("updated_at", -1)
    )

    # For each session, load its messages from chat_messages
    sessions = []
    for raw in raw_sessions:
        chat_id = raw.get("id")
        messages = list(
            db["chat_messages"]
            .find({"user_id": user_id, "chat_id": chat_id}, {"_id": 0, "user_id": 0, "chat_id": 0})
            .sort("created_at", 1)
        )
        raw["messages"] = messages
        sessions.append(raw)

    next_id = _infer_next_chat_id(sessions)
    active = sessions[0]["id"] if sessions else None

    logger.info(
        "Chat state loaded — uid=%s sessions=%d", user_id, len(sessions)
    )
    return {
        "chat_sessions": sessions,
        "active_chat_id": active,
        "next_chat_session_id": next_id,
    }


def save_chat_state(
    db: Database,
    user_id: str,
    sessions: list[dict],
    active_chat_id: str | None,
    next_chat_session_id: int,
) -> None:
    """Persist all chat sessions + messages for *user_id*.

    Upserts each session document. Replaces all messages for updated sessions.
    Does NOT touch sessions belonging to other users.
    """
    now = _now()
    session_ids = []
    for session in sessions:
        chat_id = session.get("id")
        if not chat_id:
            continue
        session_ids.append(chat_id)

        messages = session.get("messages") or []
        session_doc = {k: v for k, v in session.items() if k != "messages"}
        session_doc["user_id"] = user_id
        session_doc.setdefault("created_at", now)
        session_doc["updated_at"] = now

        db["chat_sessions"].update_one(
            {"user_id": user_id, "id": chat_id},
            {"$set": session_doc},
            upsert=True,
        )

        # Replace messages: delete existing, re-insert
        db["chat_messages"].delete_many({"user_id": user_id, "chat_id": chat_id})
        if messages:
            msg_docs = []
            for i, msg in enumerate(messages):
                doc = dict(msg)
                doc["user_id"] = user_id
                doc["chat_id"] = chat_id
                doc.setdefault("created_at", now)
                msg_docs.append(doc)
            db["chat_messages"].insert_many(msg_docs)

    # Remove sessions that no longer exist for this user
    if session_ids:
        db["chat_sessions"].delete_many(
            {"user_id": user_id, "id": {"$nin": session_ids}}
        )
        db["chat_messages"].delete_many(
            {"user_id": user_id, "chat_id": {"$nin": session_ids}}
        )

    logger.info(
        "Chat state saved — uid=%s sessions=%d active=%s",
        user_id,
        len(sessions),
        active_chat_id,
    )
