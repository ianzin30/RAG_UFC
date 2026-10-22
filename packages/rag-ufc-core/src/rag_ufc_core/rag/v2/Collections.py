"""Markdown collection loading and content hashes, independent of retrieval."""

import hashlib
from pathlib import Path
from langchain_core.documents import Document

ROOT_COLLECTION_KEY = "__root__"
UPLOAD_COLLECTION_NAME = "uploaded_files"


def normalize_collection_selection(collections) -> list[str]:
    """Deduplicated, stripped names with the root collection first."""
    if collections is None:
        return []
    items = [collections] if isinstance(collections, str) else list(collections)
    normalized, seen = [], set()
    for item in items:
        name = str(item or "").strip()
        if name and name not in seen:
            seen.add(name)
            normalized.append(name)
    return sorted(normalized, key=lambda name: (name != ROOT_COLLECTION_KEY, name.lower()))


def format_collection_selection_label(collections) -> str:
    selected = normalize_collection_selection(collections)
    if not selected:
        return "colecao nao identificada"
    if len(selected) == 1:
        return "Uploaded files" if selected[0] == UPLOAD_COLLECTION_NAME else selected[0]
    return ", ".join(selected)


class CollectionStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _files(self, names):
        for name in names:
            # The upload surface represents all local collections, as in V1/V2.
            path = self.root if name in {ROOT_COLLECTION_KEY, UPLOAD_COLLECTION_NAME} else self.root / name
            if not path.exists():
                raise ValueError(f"Collection '{name}' not found.")
            files = sorted(p for p in path.rglob("*.md") if p.is_file())
            if not files:
                raise ValueError(f"No documents found in collection '{name}'.")
            yield name, files

    def enumerate(self, names):
        records = {}
        for _, files in self._files(names):
            for path in files:
                relative = path.relative_to(self.root).as_posix()
                records[relative] = {
                    "relative_path": relative,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
        return [records[key] for key in sorted(records)]

    def load(self, names):
        documents = []
        for name, files in self._files(names):
            for path in files:
                documents.append(Document(
                    page_content=path.read_text(encoding="utf-8"),
                    metadata={"source": str(path), "collection_name": name},
                ))
        return documents
