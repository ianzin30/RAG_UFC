from __future__ import annotations

from copy import deepcopy

# Normalization and labels are engine-owned; the toggles below are UI helpers.
from rag_ufc_core.rag.v2.Collections import (  # noqa: F401
    ROOT_COLLECTION_KEY,
    format_collection_selection_label,
    normalize_collection_selection,
)


def clone_collection_selection(collections):
    normalized = normalize_collection_selection(collections)
    return deepcopy(normalized) if normalized else None


def toggle_collection_selection(collections, collection_name: str | None):
    name = str(collection_name or "").strip()
    selected = normalize_collection_selection(collections)
    if not name:
        return selected or None

    if name in selected:
        selected = [item for item in selected if item != name]
    else:
        selected.append(name)

    normalized = normalize_collection_selection(selected)
    return normalized or None


def add_collection_selection(collections, collection_name: str | None):
    name = str(collection_name or "").strip()
    if not name:
        return normalize_collection_selection(collections) or None
    normalized = normalize_collection_selection([*normalize_collection_selection(collections), name])
    return normalized or None


def sanitize_collection_selection(collections, available_collections) -> list[str]:
    available = set(normalize_collection_selection(available_collections))
    return [item for item in normalize_collection_selection(collections) if item in available]


def is_collection_selected(collections, collection_name: str) -> bool:
    return str(collection_name or "").strip() in normalize_collection_selection(collections)
