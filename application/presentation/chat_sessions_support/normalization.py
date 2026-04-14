"""Normalization helpers for persisted chat sessions."""

import re
from copy import deepcopy
from datetime import datetime, timezone

import streamlit as st

from presentation.collection_selection import clone_collection_selection

from .constants import DEFAULT_CHAT_TITLE


def coerce_messages(messages) -> list[dict[str, object]]:
    normalized_messages: list[dict[str, object]] = []
    for message in list(messages or []):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", ""))
        if not role:
            continue

        normalized_message: dict[str, object] = {"role": role, "content": content}
        route = str(message.get("route", "")).strip().lower()
        if route in {"casual", "retrieval"}:
            normalized_message["route"] = route

        resolved_question = str(message.get("resolved_question", "")).strip()
        if resolved_question:
            normalized_message["resolved_question"] = resolved_question

        raw_matched_documents = message.get("matched_documents")
        if isinstance(raw_matched_documents, list):
            matched_documents = [str(document_name).strip() for document_name in raw_matched_documents if str(document_name).strip()]
            if matched_documents:
                normalized_message["matched_documents"] = matched_documents

        if bool(message.get("needs_document_refinement")):
            normalized_message["needs_document_refinement"] = True

        raw_sources = message.get("sources")
        if isinstance(raw_sources, list):
            normalized_sources = []
            for source in raw_sources:
                if not isinstance(source, dict):
                    continue
                document_name = str(source.get("document_name", "")).strip()
                chunk_kind = str(source.get("chunk_kind", "")).strip()
                excerpt = str(source.get("excerpt", "")).strip()
                if not document_name and not excerpt:
                    continue
                normalized_sources.append(
                    {
                        "document_name": document_name or "documento",
                        "chunk_kind": chunk_kind or "text",
                        "excerpt": excerpt,
                    }
                )
            if normalized_sources:
                normalized_message["sources"] = normalized_sources

        normalized_messages.append(normalized_message)
    return normalized_messages


def coerce_chat_session(chat) -> dict[str, object] | None:
    if not isinstance(chat, dict):
        return None

    chat_id = str(chat.get("id", "")).strip()
    title = str(chat.get("title", "")).strip()
    if not chat_id or not title:
        return None

    created_at = coerce_chat_timestamp(chat.get("created_at"))
    updated_at = coerce_chat_timestamp(chat.get("updated_at")) or created_at
    return {
        "id": chat_id,
        "title": title,
        "collection": clone_collection_selection(chat.get("collection")),
        "model_name": str(chat.get("model_name", "")).strip() or None,
        "messages": coerce_messages(chat.get("messages")),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def infer_next_chat_id(sessions: list[dict[str, object]]) -> int:
    highest = 0
    for chat in sessions:
        match = re.fullmatch(r"chat_(\d+)", str(chat.get("id", "")).strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def clone_messages(messages) -> list[dict[str, str]]:
    return deepcopy(list(messages or []))


def build_timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def coerce_chat_timestamp(value) -> str:
    if isinstance(value, datetime):
        normalized = value
    else:
        text = str(value or "").strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            normalized = datetime.fromisoformat(text) if text else None
        except ValueError:
            normalized = None

    if normalized is None:
        normalized = datetime.now(timezone.utc)
    elif normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=timezone.utc)
    else:
        normalized = normalized.astimezone(timezone.utc)
    return normalized.isoformat()


def build_default_title() -> str:
    titles = {chat["title"] for chat in st.session_state.get("chat_sessions", [])}
    if DEFAULT_CHAT_TITLE not in titles:
        return DEFAULT_CHAT_TITLE

    index = 2
    while f"{DEFAULT_CHAT_TITLE} {index}" in titles:
        index += 1
    return f"{DEFAULT_CHAT_TITLE} {index}"


def truncate_title(text: str, max_length: int = 34) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return build_default_title()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."
