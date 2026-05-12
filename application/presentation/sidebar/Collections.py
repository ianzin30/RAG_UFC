"""Collection discovery helpers for the shared Streamlit shell."""

import re
from pathlib import Path

from presentation.shared.Config import PROJECT_ROOT, ROOT_COLLECTION_KEY


def _get_collections_root(user_id: str | None) -> Path:
    """Return the shared local collections root."""
    _ = user_id
    return PROJECT_ROOT / "data" / "collections"


def list_collection_documents(user_id: str | None = None) -> list[dict[str, str]]:
    collections_dir = _get_collections_root(user_id)
    if not collections_dir.exists():
        return []

    documents: list[dict[str, str]] = []
    for file_path in sorted(collections_dir.glob("*.md"), key=lambda item: item.name.lower()):
        label = re.sub(r"^\d+[_\- ]*", "", file_path.stem).strip() or file_path.stem
        documents.append(
            {
                "collection": ROOT_COLLECTION_KEY,
                "file_name": file_path.name,
                "label": label,
            }
        )

    for folder in sorted(collections_dir.iterdir(), key=lambda item: item.name.lower()):
        if not folder.is_dir():
            continue

        markdown_files = sorted(folder.glob("*.md"), key=lambda item: item.name.lower())
        for file_path in markdown_files:
            label = re.sub(r"^\d+[_\- ]*", "", file_path.stem).strip() or file_path.stem
            documents.append(
                {
                    "collection": folder.name,
                    "file_name": file_path.name,
                    "label": label,
                }
            )
    return documents


def list_available_collections(documents: list[dict[str, str]]) -> list[str]:
    return sorted({document["collection"] for document in documents if document["collection"]})


def group_documents_by_collection(documents: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for document in documents:
        grouped.setdefault(document["collection"], []).append(document)
    return sorted(grouped.items(), key=lambda item: (item[0] != ROOT_COLLECTION_KEY, item[0].lower()))


def format_collection_label(collection_name: str) -> str:
    if not collection_name or collection_name == ROOT_COLLECTION_KEY:
        return ""
    return collection_name.replace("_", " ").strip()
