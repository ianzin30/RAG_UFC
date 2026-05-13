"""Collection discovery helpers for the shared Streamlit shell."""

from __future__ import annotations

import re
from pathlib import Path

from presentation.shared.Config import PROJECT_ROOT, ROOT_COLLECTION_KEY, UPLOAD_COLLECTION_NAME


def _get_collections_root(user_id: str | None) -> Path:
    """Return the shared local collections root."""
    _ = user_id
    return PROJECT_ROOT / "data" / "collections"


def list_collection_documents(user_id: str | None = None) -> list[dict[str, str]]:
    collections_dir = _get_collections_root(user_id)
    if not collections_dir.exists():
        return []

    documents: list[dict[str, str]] = []
    markdown_files = sorted(
        (path for path in collections_dir.rglob("*.md") if path.is_file()),
        key=lambda item: item.relative_to(collections_dir).as_posix().lower(),
    )
    for file_path in markdown_files:
        relative_path = file_path.relative_to(collections_dir).as_posix()
        label = re.sub(r"^\d+[_\- ]*", "", file_path.stem).strip() or file_path.stem
        documents.append(
            {
                "collection": UPLOAD_COLLECTION_NAME,
                "file_name": file_path.name,
                "relative_path": relative_path,
                "label": label,
            }
        )
    return documents


def list_available_collections(documents: list[dict[str, str]]) -> list[str]:
    return [UPLOAD_COLLECTION_NAME] if documents else []


def group_documents_by_collection(documents: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for document in documents:
        grouped.setdefault(document["collection"], []).append(document)
    return sorted(grouped.items(), key=lambda item: (item[0] != ROOT_COLLECTION_KEY, item[0].lower()))


def format_collection_label(collection_name: str) -> str:
    if not collection_name or collection_name == ROOT_COLLECTION_KEY:
        return ""
    if collection_name == UPLOAD_COLLECTION_NAME:
        return "Uploaded files"
    return collection_name.replace("_", " ").strip()
