from copy import deepcopy


ROOT_COLLECTION_KEY = "__root__"


def _collection_sort_key(collection_name: str) -> tuple[bool, str]:
    return (collection_name != ROOT_COLLECTION_KEY, collection_name.lower())


def normalize_collection_selection(collections) -> list[str]:
    if collections is None:
        return []

    if isinstance(collections, str):
        items = [collections]
    else:
        items = list(collections)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)

    return sorted(normalized, key=_collection_sort_key)


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


def format_collection_selection_label(collections) -> str:
    selected = normalize_collection_selection(collections)
    if not selected:
        return "colecao nao identificada"
    if len(selected) == 1:
        return selected[0]
    return ", ".join(selected)
